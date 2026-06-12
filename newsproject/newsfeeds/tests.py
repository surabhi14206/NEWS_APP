from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from .models import NewsArticle

class ManualAnalysisTestCase(TestCase):
    def setUp(self):
        # Create a regular relevant article to verify sidebar listing works
        self.relevant_article = NewsArticle.objects.create(
            title="Relevant Article",
            link="http://example.com/1",
            source="Test Source",
            published_date=timezone.now(),
            is_relevant=True,
            summary="A valid summary of relevant news."
        )

    def test_manual_save_view(self):
        url = reverse('manual_analysis')
        post_data = {
            'save': 'true',
            'title': 'Manual Article',
            'link': 'http://example.com/2',
            'source': 'Manual Source',
            'published_date': '01 Jun 2026',
            'description': 'Manual article description.',
            'summary': 'Manual article summary.',
            'reason': 'Analyzed manually.',
            'matched_keywords[]': ['economy', 'gdp'],
            'event_class': 'Macro_Economy',
            'sector': 'General / Macro',
            'sub_type': 'General_Terms (General)',
            'channel': 'Macroeconomic Transmission',
            'direction': 'positive',
            'impact_score': 3,
            'direction_reason': 'Positive GDP growth.',
            'origin': 'India'
        }
        
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue(data['saved'])
        
        # Verify the saved object in DB has is_relevant=False
        article_id = data['article']['id']
        article = NewsArticle.objects.get(id=article_id)
        self.assertEqual(article.title, 'Manual Article')
        self.assertFalse(article.is_relevant)

    def test_dashboard_exclusions_and_selection(self):
        # 1. Create a manually saved article (is_relevant=False)
        manual_article = NewsArticle.objects.create(
            title="Manual Saved Article",
            link="http://example.com/manual",
            source="Manual Source",
            published_date=timezone.now(),
            is_relevant=False,
            summary="A valid summary of manual news."
        )

        dashboard_url = reverse('dashboard')
        
        # 2. Get dashboard without selection: manual_article should NOT be in primary list
        response = self.client.get(dashboard_url)
        self.assertEqual(response.status_code, 200)
        articles = response.context['articles']
        self.assertIn(self.relevant_article, articles)
        self.assertNotIn(manual_article, articles)
        
        # Verify manual_articles context variable contains our manual saved article
        self.assertIn(manual_article, response.context['manual_articles'])

        # 3. Get dashboard with manual_article select: should be in selected_article context
        response = self.client.get(f"{dashboard_url}?select={manual_article.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['selected_article'], manual_article)
        
        # Verify that context['articles'] still excludes manual_article
        articles = response.context['articles']
        self.assertNotIn(manual_article, articles)

    def test_parse_multiple_manual_contents(self):
        from newsfeeds.management.commands.manual_analysis import parse_multiple_manual_contents
        
        raw_text = """
        title: Article One
        link: http://example.com/one
        description: Description one.
        source: Source One
        published_date: 01 Jun 2026

        title: Article Two
        link: http://example.com/two
        description: Description two.
        source: Source Two
        published_date: 02 Jun 2026
        """
        
        parsed = parse_multiple_manual_contents(raw_text)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]['title'], 'Article One')
        self.assertEqual(parsed[0]['link'], 'http://example.com/one')
        self.assertEqual(parsed[1]['title'], 'Article Two')
        self.assertEqual(parsed[1]['link'], 'http://example.com/two')

    def test_manual_delete_view(self):
        # Create a manually saved article
        manual_article = NewsArticle.objects.create(
            title="Manual Article to Delete",
            link="http://example.com/delete",
            source="Manual Source",
            published_date=timezone.now(),
            is_relevant=False,
            summary="Test summary"
        )
        
        url = reverse('manual_analysis')
        
        # Test delete operation
        post_data = {
            'delete': 'true',
            'article_id': manual_article.id
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue(data['deleted'])
        
        # Verify it has been deleted from DB
        self.assertFalse(NewsArticle.objects.filter(id=manual_article.id).exists())

    def test_manual_save_duplicate_view(self):
        from newsfeeds.models import DuplicateNewsArticle
        from dateutil import parser as date_parser
        from django.utils.timezone import make_aware
        
        dt = date_parser.parse('01 Jun 2026')
        dt_aware = make_aware(dt)
        
        # 1. Create initial article in main NewsArticle table
        NewsArticle.objects.create(
            title="Duplicate Title Test",
            link="http://example.com/dup",
            source="Source",
            published_date=dt_aware,
            is_relevant=True,
            summary="Original article."
        )

        url = reverse('manual_analysis')
        post_data = {
            'save': 'true',
            'title': 'Duplicate Title Test',
            'link': 'http://example.com/dup',
            'source': 'Manual Source',
            'published_date': '01 Jun 2026',
            'description': 'Description for duplicate.',
            'summary': 'Summary for duplicate.',
            'reason': 'Analyzed manually.',
            'matched_keywords[]': ['economy'],
            'event_class': 'Macro_Economy',
            'sector': 'General / Macro',
            'sub_type': 'General_Terms (General)',
            'channel': 'Macroeconomic Transmission',
            'direction': 'positive',
            'impact_score': 1,
            'direction_reason': 'Reason.',
            'origin': 'India'
        }
        
        # 2. Save the duplicate manual article (all 3 parameter match -> reject/save as duplicate)
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue(data['saved'])
        self.assertTrue(data['is_duplicate'])
        self.assertTrue(str(data['article']['id']).startswith('dup-'))

        # 3. Verify it is saved in DuplicateNewsArticle database
        dup_id = data['article']['id'].split('dup-')[1]
        self.assertTrue(DuplicateNewsArticle.objects.filter(id=dup_id).exists())

        # 4. Check dashboard list has both manual articles
        dashboard_url = reverse('dashboard')
        resp = self.client.get(dashboard_url)
        self.assertEqual(resp.status_code, 200)
        manual_articles = resp.context['manual_articles']
        custom_ids = [art.custom_id for art in manual_articles]
        self.assertIn(f"dup-{dup_id}", custom_ids)

        # 5. Delete duplicate article
        delete_post = {
            'delete': 'true',
            'article_id': f"dup-{dup_id}"
        }
        del_resp = self.client.post(url, delete_post)
        self.assertEqual(del_resp.status_code, 200)
        self.assertTrue(del_resp.json()['deleted'])
        self.assertFalse(DuplicateNewsArticle.objects.filter(id=dup_id).exists())

    def test_manual_save_non_duplicate_different_link_date_view(self):
        from dateutil import parser as date_parser
        from django.utils.timezone import make_aware
        
        dt = date_parser.parse('01 Jun 2026')
        dt_aware = make_aware(dt)
        
        # 1. Create initial article in main NewsArticle table
        NewsArticle.objects.create(
            title="Same Title Different Link Date",
            link="http://example.com/original-link",
            source="Source",
            published_date=dt_aware,
            is_relevant=True,
            summary="Original article."
        )

        url = reverse('manual_analysis')
        # Same title, but link and date are different -> should be kept in main table
        post_data = {
            'save': 'true',
            'title': 'Same Title Different Link Date',
            'link': 'http://example.com/different-link',
            'source': 'Manual Source',
            'published_date': '02 Jun 2026',
            'description': 'Description.',
            'summary': 'Summary.',
            'reason': 'Analyzed manually.',
            'matched_keywords[]': ['economy'],
            'event_class': 'Macro_Economy',
            'sector': 'General / Macro',
            'sub_type': 'General_Terms (General)',
            'channel': 'Macroeconomic Transmission',
            'direction': 'positive',
            'impact_score': 1,
            'direction_reason': 'Reason.',
            'origin': 'India'
        }
        
        # 2. Save the article (should NOT be duplicate)
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue(data['saved'])
        self.assertFalse(data.get('is_duplicate', False))
        
        # Verify it was saved/updated in main NewsArticle table (created=True or updated=True)
        article_id = data['article']['id']
        self.assertTrue(NewsArticle.objects.filter(id=article_id).exists())

    def test_general_macro_blanking_in_view(self):
        url = reverse('manual_analysis')
        post_data = {
            'save': 'true',
            'title': 'General Macro Blanking Test',
            'link': 'http://example.com/blank',
            'source': 'Manual Source',
            'published_date': '01 Jun 2026',
            'description': 'Description.',
            'summary': 'Summary.',
            'reason': 'Analyzed manually.',
            'event_class': 'Macro_Economy',
            'sector': 'General / Macro',
            'sub_type': 'General_Terms (General)',
            'channel': 'Macroeconomic Transmission',
            'direction': 'positive',
            'impact_score': 3,
            'direction_reason': 'Positive GDP growth.',
            'origin': 'India'
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        
        article_id = data['article']['id']
        article = NewsArticle.objects.get(id=article_id)
        self.assertEqual(article.event_class, "")
        self.assertEqual(article.sector, "")

    def test_general_macro_blanking_in_process_manual_article(self):
        from newsfeeds.management.commands.manual_analysis import process_manual_article
        from unittest.mock import patch
        
        # Mocking classification response to return general/macro
        mock_classification = {
            'event_class': 'Macro_Economy',
            'sector': 'General / Macro',
            'sub_type': 'General_Terms (General)',
            'channel': 'Macroeconomic Transmission'
        }
        
        test_art = {
            'title': 'CLI General Macro Test',
            'link': 'http://example.com/cli-blank',
            'description': 'Test article description.',
            'source': 'CLI Source',
            'published_date': '01 Jun 2026'
        }
        
        with patch('newsfeeds.management.commands.fetch_indian_economy_news.classify_article_with_ollama', return_value=mock_classification):
            with patch('newsfeeds.management.commands.fetch_indian_economy_news.generate_summary', return_value='summary'):
                with patch('newsfeeds.management.commands.fetch_indian_economy_news.analyze_direction_from_india_view', return_value={'direction': 'neutral', 'impact_score': 0, 'reason': ''}):
                    res = process_manual_article(test_art, save_to_db=True)
                    self.assertEqual(res['status'], 'success')
                    self.assertTrue(res['saved'])
                    
                    # Verify saved article
                    article = NewsArticle.objects.get(title='CLI General Macro Test')
                    self.assertEqual(article.event_class, "")
                    self.assertEqual(article.sector, "")

    def test_fetch_command_startup_cleanup_excludes_global_factors(self):
        from django.core.management import call_command
        from unittest.mock import patch
        
        # 1. Create articles in DB
        # This one should be deleted (event_class is general macro)
        macro_article = NewsArticle.objects.create(
            title="General Macro Article",
            link="http://example.com/macro",
            source="Test",
            published_date=timezone.now(),
            event_class="Macro_Economy",
            sector="General / Macro",
            is_relevant=True,
            summary="Summary"
        )
        
        # This one should NOT be deleted (event_class is Global_Factors)
        global_article = NewsArticle.objects.create(
            title="Global Factors Article",
            link="http://example.com/global",
            source="Test",
            published_date=timezone.now(),
            event_class="Global_Factors",
            sector="General / Macro",
            is_relevant=True,
            summary="Summary"
        )
        
        # 2. Call command with RSS_FEEDS mocked to be empty so it finishes immediately
        with patch('newsfeeds.management.commands.fetch_indian_economy_news.RSS_FEEDS', {}):
            call_command('fetch_indian_economy_news')
        
        # 3. Assert macro_article is deleted and global_article is NOT deleted
        self.assertFalse(NewsArticle.objects.filter(id=macro_article.id).exists())
        self.assertTrue(NewsArticle.objects.filter(id=global_article.id).exists())

