from django.shortcuts import render, redirect
from django.views.generic import ListView
from newsfeeds.models import NewsArticle, DuplicateNewsArticle

class DashboardView(ListView):
    model = NewsArticle
    template_name = 'dashboard.html'
    context_object_name = 'articles'

    def get_queryset(self):
        # Only show articles that have a valid summary and insights/reason
        qs = NewsArticle.objects.filter(is_relevant=True)
        qs = qs.exclude(summary__in=['', 'Summary could not be generated.', 'Summary could not be completed.', 'Summary could not be generated'])
        qs = qs.exclude(reason__icontains='Ollama is offline')
        return qs.order_by('-published_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get normal manual articles
        manual_list = list(NewsArticle.objects.filter(is_relevant=False).order_by('-published_date'))
        for item in manual_list:
            item.custom_id = str(item.id)
            item.is_duplicate = False

        # Get duplicate manual articles
        dup_list = list(DuplicateNewsArticle.objects.all().order_by('-published_date'))
        for item in dup_list:
            item.custom_id = f"dup-{item.id}"
            item.is_duplicate = True

        # Combine and sort by published_date descending
        combined_manual = manual_list + dup_list
        combined_manual.sort(key=lambda x: x.published_date, reverse=True)
        context['manual_articles'] = combined_manual

        select_id = self.request.GET.get('select')
        if select_id:
            try:
                if str(select_id).startswith('dup-'):
                    context['selected_article'] = DuplicateNewsArticle.objects.get(id=select_id.split('dup-')[1])
                else:
                    context['selected_article'] = NewsArticle.objects.get(id=select_id)
            except (NewsArticle.DoesNotExist, DuplicateNewsArticle.DoesNotExist):
                pass
        return context

import threading
from django.contrib import messages
from django.conf import settings

def check_and_start_ollama(relevance_model='news_filter_custom:latest', classifier_model='gemma3:4b'):
    import requests
    import subprocess
    import time
    
    ollama_running = False
    try:
        r = requests.get("http://localhost:11434/", timeout=0.5)
        ollama_running = (r.status_code == 200)
    except Exception:
        ollama_running = False
        
    if not ollama_running:
        try:
            # Launch "ollama serve" in the background
            subprocess.Popen("ollama serve", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for _ in range(15):
                time.sleep(1)
                try:
                    r = requests.get("http://localhost:11434/", timeout=0.5)
                    if r.status_code == 200:
                        ollama_running = True
                        break
                except Exception:
                    pass
        except Exception:
            pass
            
    if ollama_running:
        try:
            # Pre-warm models synchronously to ensure they are loaded in memory
            requests.post("http://localhost:11434/api/generate", json={"model": relevance_model}, timeout=60)
            requests.post("http://localhost:11434/api/generate", json={"model": classifier_model}, timeout=60)
        except Exception:
            try:
                # Fallback to synchronous subprocess run if API call fails
                subprocess.run(f"ollama run {relevance_model} \"\"", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
                subprocess.run(f"ollama run {classifier_model} \"\"", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
            except Exception:
                pass
            
    return ollama_running

def trigger_fetch(request):
    relevance_model = getattr(settings, 'OLLAMA_RELEVANCE_MODEL', 'news_filter_custom:latest')
    classifier_model = getattr(settings, 'OLLAMA_MODEL', 'gemma3:4b')
    
    ollama_running = check_and_start_ollama(relevance_model, classifier_model)
    
    if not ollama_running:
        messages.error(request, "Error: Ollama is not running and could not be started automatically. Please run Ollama manually.")
        return redirect('dashboard')

    # For manual trigger from dashboard, run in background thread
    from django.core.management import call_command
    
    def fetch_task():
        try:
            call_command('fetch_indian_economy_news')
        except Exception as e:
            print(f"Fetch failed: {e}")
            
    thread = threading.Thread(target=fetch_task)
    thread.start()
    
    messages.success(request, "News fetching started in the background! Please wait a few minutes and refresh the page to see new articles.")
    return redirect('dashboard')


from django.http import JsonResponse
from newsfeeds.management.commands.manual_analysis import parse_manual_content, process_manual_article, read_docx_text, parse_multiple_manual_contents

def manual_analysis_view(request):
    if request.method == 'POST':
        # Check if this is a delete operation
        if request.POST.get('delete') == 'true':
            article_id = request.POST.get('article_id')
            if not article_id:
                return JsonResponse({'status': 'error', 'message': 'Article ID is required to delete.'}, status=400)
            try:
                if str(article_id).startswith('dup-'):
                    real_id = article_id.split('dup-')[1]
                    DuplicateNewsArticle.objects.filter(id=real_id).delete()
                else:
                    NewsArticle.objects.filter(id=article_id, is_relevant=False).delete()
                return JsonResponse({'status': 'success', 'deleted': True})
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': f'Failed to delete article: {str(e)}'}, status=500)

        # Check and start Ollama automatically before manual analysis/save operations
        relevance_model = getattr(settings, 'OLLAMA_RELEVANCE_MODEL', 'news_filter_custom:latest')
        classifier_model = getattr(settings, 'OLLAMA_MODEL', 'gemma3:4b')
        ollama_running = check_and_start_ollama(relevance_model, classifier_model)
            
        if not ollama_running:
            return JsonResponse({'status': 'error', 'message': 'Ollama is not running and could not be started automatically. Please start the Ollama service locally before performing manual analysis.'}, status=503)

        # Check if this is a save operation
        if request.POST.get('save') == 'true':
            from datetime import datetime
            from django.utils.timezone import make_aware
            from dateutil import parser as date_parser
            from django.db.models import Q
            
            try:
                title = request.POST.get('title')
                if not title:
                    return JsonResponse({'status': 'error', 'message': 'Title is required to save.'}, status=400)
                
                # Parse date
                published_date_str = request.POST.get('published_date')
                try:
                    dt = date_parser.parse(published_date_str)
                    dt_aware = make_aware(dt)
                except Exception:
                    dt_aware = datetime.now()
                
                # Extract keywords list
                matched_kws = request.POST.getlist('matched_keywords[]') or request.POST.get('matched_keywords', '')
                if isinstance(matched_kws, str):
                    matched_kws = [kw.strip() for kw in matched_kws.split(',') if kw.strip()]

                link = request.POST.get('link', '#') or '#'
                
                # Extract and clean event_class and sector values
                event_class_val = request.POST.get('event_class', 'Macro_Economy') or 'Macro_Economy'
                sector_val = request.POST.get('sector', 'General / Macro') or 'General / Macro'
                if any(w in event_class_val.lower() for w in ("macro", "general")):
                    event_class_val = ""
                if any(w in sector_val.lower() for w in ("macro", "general")):
                    sector_val = ""

                # Duplicate check: check if title, link, and date all match an existing entry in DB
                if NewsArticle.objects.filter(
                    title=title,
                    link=link,
                    published_date=dt_aware
                ).exists():
                    article_obj = DuplicateNewsArticle.objects.create(
                        title=title,
                        link=link,
                        source=request.POST.get('source', 'Economic News') or 'Economic News',
                        published_date=dt_aware,
                        description=request.POST.get('description', ''),
                        full_text=request.POST.get('description', ''),
                        summary=request.POST.get('summary', ''),
                        reason=request.POST.get('reason', ''),
                        matched_keywords=matched_kws,
                        is_relevant=False,
                        event_class=event_class_val,
                        sector=sector_val,
                        sub_type=request.POST.get('sub_type', 'General_Terms (General)'),
                        channel=request.POST.get('channel', 'Macroeconomic Transmission'),
                        direction=request.POST.get('direction', 'neutral'),
                        impact_score=int(request.POST.get('impact_score', 0) or 0),
                        direction_reason=request.POST.get('direction_reason', ''),
                        origin=request.POST.get('origin', 'Global') or 'Global'
                    )
                    return JsonResponse({
                        'status': 'success',
                        'saved': True,
                        'created': True,
                        'is_duplicate': True,
                        'article': {
                            'id': f"dup-{article_obj.id}",
                            'title': article_obj.title
                        }
                    })
                else:
                    article_obj, created = NewsArticle.objects.update_or_create(
                        title=title,
                        link=link,
                        published_date=dt_aware,
                        defaults={
                            'source': request.POST.get('source', 'Economic News') or 'Economic News',
                            'description': request.POST.get('description', ''),
                            'full_text': request.POST.get('description', ''),
                            'summary': request.POST.get('summary', ''),
                            'reason': request.POST.get('reason', ''),
                            'matched_keywords': matched_kws,
                            'is_relevant': False,
                            
                            # Taxonomy
                            'event_class': event_class_val,
                            'sector': sector_val,
                            'sub_type': request.POST.get('sub_type', 'General_Terms (General)'),
                            'channel': request.POST.get('channel', 'Macroeconomic Transmission'),
                            
                            # Sentiment
                            'direction': request.POST.get('direction', 'neutral'),
                            'impact_score': int(request.POST.get('impact_score', 0) or 0),
                            'direction_reason': request.POST.get('direction_reason', ''),
                            
                            # Origin
                            'origin': request.POST.get('origin', 'Global') or 'Global'
                        }
                    )
                    return JsonResponse({
                        'status': 'success',
                        'saved': True,
                        'created': created,
                        'is_duplicate': False,
                        'article': {
                            'id': str(article_obj.id),
                            'title': article_obj.title
                        }
                    })
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': f'Failed to save article: {str(e)}'}, status=500)

        # Standard manual analysis path (Analyze only - does not save)
        raw_text = ""
        # 1. Check for file upload
        uploaded_file = request.FILES.get('file')
        if uploaded_file:
            filename = uploaded_file.name.lower()
            try:
                if filename.endswith('.docx'):
                    raw_text = read_docx_text(uploaded_file)
                elif filename.endswith('.txt') or filename.endswith('.doc'):
                    raw_text = uploaded_file.read().decode('utf-8', errors='ignore')
                else:
                    return JsonResponse({'status': 'error', 'message': 'Unsupported file format. Please upload a .txt or .docx file.'}, status=400)
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': f'Failed to read file: {str(e)}'}, status=400)
        else:
            # 2. Check for pasted text
            raw_text = request.POST.get('text', '')

        raw_text = raw_text.strip()
        if not raw_text:
            return JsonResponse({'status': 'error', 'message': 'No content provided. Please upload a file or paste text.'}, status=400)

        # 3. Parse content
        parsed_articles = parse_multiple_manual_contents(raw_text)
        if not parsed_articles:
            return JsonResponse({
                'status': 'error', 
                'message': 'Failed to parse any articles from content. Please make sure the text contains at least one "title: <Headline>" on its own line.'
            }, status=400)

        # 4. Process and run pipeline
        results = []
        for index, art in enumerate(parsed_articles):
            try:
                res = process_manual_article(art, save_to_db=False)
                if res.get('status') == 'success':
                    results.append(res.get('article'))
            except Exception as e:
                print(f"Failed to process manual article {index}: {e}")

        if not results:
            return JsonResponse({'status': 'error', 'message': 'Analysis pipeline failed for all identified articles.'}, status=500)

        return JsonResponse({
            'status': 'success',
            'articles': results
        })

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)