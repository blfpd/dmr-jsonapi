from dmr.routing import Router, path

from server import views

router = Router(
    'api/',
    [
        path('articles/', views.ArticlesController.as_view(), name='articles'),
        path(
            'articles/<int:article_id>/',
            views.ArticleController.as_view(),
            name='article',
        ),
        path(
            'async/articles/',
            views.AsyncArticlesController.as_view(),
            name='async_articles',
        ),
        path(
            'async/articles/<int:article_id>/',
            views.AsyncArticleController.as_view(),
            name='async_article',
        ),
    ],
)

urlpatterns = [router.to_urlpatterns(namespace='api')]
