import React, { useState } from 'react';
import { Container, Typography, Box, Grid, Card, CardContent, Button, Chip, Dialog, DialogTitle, DialogContent, DialogActions } from '@mui/material';
import TerminalLayout from '../components/TerminalLayout';
import NewsCard from '../components/Dashboard/NewsCard';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorDisplay from '../components/ErrorDisplay';
import { newsApi } from '../services/api';
import useApi from '../hooks/useApi';
import { useAppContext } from '../context/AppContext';
import ProtectedRoute from '../components/common/ProtectedRoute';
import '../styles/components.css';
import '../styles/animations.css';
import '../styles/retro.css';

const News = () => {
  const [page, setPage] = useState(0);
  const [selectedArticle, setSelectedArticle] = useState(null);
  const [viewMode, setViewMode] = useState('articles'); // 'articles' or 'summaries'
  const limit = 10;
  const offset = page * limit;

  const { data: articlesData, loading: articlesLoading, error: articlesError, refetch: refetchArticles } = useApi(
    () => newsApi.getArticles(limit, offset),
    [page, viewMode],
    viewMode === 'articles'
  );

  const { data: summariesData, loading: summariesLoading, error: summariesError, refetch: refetchSummaries } = useApi(
    () => newsApi.getSummaries(limit, 0.3),
    [viewMode],
    viewMode === 'summaries'
  );

  const articles = viewMode === 'articles' ? (articlesData?.data || []) : [];
  const summaries = viewMode === 'summaries' ? (summariesData?.data?.summaries || []) : [];
  const pagination = articlesData?.pagination || {};

  const handleArticleClick = async (article) => {
    try {
      const fullArticle = await newsApi.getArticle(article.article_id || article.id);
      setSelectedArticle(fullArticle?.data || article);
    } catch (error) {
      setSelectedArticle(article);
    }
  };

  return (
    <ProtectedRoute>
    <TerminalLayout>
        <div className="crt-overlay" />
        <div className="scanlines" />
        
        <Container maxWidth="xl" sx={{ py: { xs: 4, md: 8 }, position: 'relative', zIndex: 1 }}>
          <Box className="fade-in" sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Box>
              <Typography variant="h1" component="h1" gutterBottom className="retro-glow">
          FPL News
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Chip
                label="Articles"
                onClick={() => setViewMode('articles')}
                color={viewMode === 'articles' ? 'primary' : 'default'}
                sx={{ fontFamily: "'JetBrains Mono', monospace" }}
              />
              <Chip
                label="AI Summaries"
                onClick={() => setViewMode('summaries')}
                color={viewMode === 'summaries' ? 'primary' : 'default'}
                sx={{ fontFamily: "'JetBrains Mono', monospace" }}
              />
            </Box>
          </Box>

          {(articlesLoading || summariesLoading) && (
            <LoadingSpinner message="Loading..." />
          )}

          {(articlesError || summariesError) && (
            <ErrorDisplay 
              error={articlesError || summariesError} 
              onRetry={viewMode === 'articles' ? refetchArticles : refetchSummaries} 
            />
      )}

          {!articlesLoading && !summariesLoading && !articlesError && !summariesError && (
        <>
              <Grid container spacing={3} className="fade-in-delay-1">
                {(viewMode === 'articles' ? articles : summaries).map((item, idx) => (
                  <Grid item xs={12} sm={6} md={4} key={item.article_id || item.id || idx}>
                    <NewsCard 
                      article={item} 
                      onClick={() => handleArticleClick(item)}
                      isSummary={viewMode === 'summaries'}
                    />
                  </Grid>
            ))}
              </Grid>

              {((viewMode === 'articles' ? articles : summaries).length === 0) && (
                <Box sx={{ textAlign: 'center', py: 8 }}>
                  <Typography color="text.secondary">
                    No data
                  </Typography>
                </Box>
          )}

              {viewMode === 'articles' && pagination && (
                <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mt: 4, alignItems: 'center' }}>
                  <Button
                    variant="outlined"
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={!pagination.has_prev}
                    sx={{ fontFamily: "'JetBrains Mono', monospace" }}
              >
                Previous
                  </Button>
                  <Typography variant="body2" color="text.secondary" sx={{ fontFamily: "'JetBrains Mono', monospace" }}>
                Page {pagination.page || page + 1} of {pagination.total_pages || 1}
                  </Typography>
                  <Button
                    variant="outlined"
                onClick={() => setPage(p => p + 1)}
                disabled={!pagination.has_next}
                    sx={{ fontFamily: "'JetBrains Mono', monospace" }}
              >
                Next
                  </Button>
                </Box>
              )}
            </>
          )}

          {/* Article Detail Modal */}
          <Dialog
            open={!!selectedArticle}
            onClose={() => setSelectedArticle(null)}
            maxWidth="md"
            fullWidth
            PaperProps={{
              sx: {
                bgcolor: '#292929',
                border: '1px solid rgba(226, 222, 218, 0.2)',
              },
            }}
          >
            {selectedArticle && (
              <>
                <DialogTitle className="retro-text">
                  {selectedArticle.title || selectedArticle.headline}
                </DialogTitle>
                <DialogContent>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    {selectedArticle.published_at && new Date(selectedArticle.published_at).toLocaleDateString()}
                  </Typography>
                  <Typography variant="body1" sx={{ mt: 2, whiteSpace: 'pre-wrap' }}>
                    {selectedArticle.content || selectedArticle.summary || selectedArticle.text}
                  </Typography>
                  {selectedArticle.url && (
                    <Button
                      href={selectedArticle.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      sx={{ mt: 2 }}
                    >
                      Read Full Article
                    </Button>
          )}
                </DialogContent>
                <DialogActions>
                  <Button onClick={() => setSelectedArticle(null)} sx={{ fontFamily: "'JetBrains Mono', monospace" }}>
                    Close
                  </Button>
                </DialogActions>
        </>
      )}
          </Dialog>
        </Container>
    </TerminalLayout>
    </ProtectedRoute>
  );
};

export default News;

