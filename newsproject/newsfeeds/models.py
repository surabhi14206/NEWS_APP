from django.db import models
from django.utils import timezone

class NewsArticle(models.Model):
    title = models.CharField(max_length=3000)
    link = models.URLField(max_length=3000)
    source = models.CharField(max_length=200)
    published_date = models.DateTimeField()
    description = models.TextField(blank=True)
    full_text = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    reason = models.TextField(blank=True)           # LLM insight
    matched_keywords = models.JSONField(default=list)
    is_relevant = models.BooleanField(default=True)
    
    # Taxonomy classification fields
    event_class = models.CharField(max_length=200, blank=True, default='Economic Impact')
    sector = models.CharField(max_length=200, blank=True, default='General / Macro')
    sub_type = models.CharField(max_length=200, blank=True, default='General News')
    channel = models.CharField(max_length=200, blank=True, default='News & Media')
    origin = models.CharField(max_length=500, blank=True, default='')
    
    # Direction / Sentiment Analysis
    DIRECTION_CHOICES = [
        ('positive', 'Positive'),
        ('negative', 'Negative'),
        ('neutral', 'Neutral'),
        ('pending', 'Pending'),
    ]
    direction = models.CharField(
        max_length=20,
        choices=DIRECTION_CHOICES,
        default='pending'
    )
    direction_reason = models.TextField(blank=True)
    impact_score = models.SmallIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-published_date']
        indexes = [models.Index(fields=['published_date', 'source'])]
        unique_together = ('title', 'link', 'published_date')

    def __str__(self):
        return f"{self.source}: {self.title[:80]}"


class DuplicateNewsArticle(models.Model):
    title = models.CharField(max_length=1000)  # NOT unique
    link = models.URLField(max_length=1000)
    source = models.CharField(max_length=200)
    published_date = models.DateTimeField()
    description = models.TextField(blank=True)
    full_text = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    reason = models.TextField(blank=True)           # LLM insight
    matched_keywords = models.JSONField(default=list)
    is_relevant = models.BooleanField(default=True)
    
    # Taxonomy classification fields
    event_class = models.CharField(max_length=200, blank=True, default='Economic Impact')
    sector = models.CharField(max_length=200, blank=True, default='General / Macro')
    sub_type = models.CharField(max_length=200, blank=True, default='General News')
    channel = models.CharField(max_length=200, blank=True, default='News & Media')
    origin = models.CharField(max_length=500, blank=True, default='')
    
    # Direction / Sentiment Analysis
    direction = models.CharField(
        max_length=20,
        choices=NewsArticle.DIRECTION_CHOICES,
        default='pending'
    )
    direction_reason = models.TextField(blank=True)
    impact_score = models.SmallIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-published_date']
        indexes = [models.Index(fields=['published_date', 'source'])]

    def __str__(self):
        return f"[DUPLICATE] {self.source}: {self.title[:80]}"