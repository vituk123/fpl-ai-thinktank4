import React from 'react';
import DashboardCard from './DashboardCard';
import { formatDate, truncateText } from '../../utils/formatters';
import '../../styles/components.css';

const NewsCard = ({ article, onClick, isSummary = false }) => {
  if (!article) return null;

  return (
    <DashboardCard onClick={onClick}>
      <h4 style={{ marginBottom: '0.75rem' }}>
        {truncateText(article.title || article.headline, 60)}
      </h4>
      {(article.description || article.summary) && (
        <p style={{ 
          marginBottom: '0.75rem', 
          color: 'var(--text-secondary)',
          fontSize: '0.875rem',
          lineHeight: '1.5'
        }}>
          {truncateText(article.description || article.summary, 150)}
        </p>
      )}
      {isSummary && article.relevance_score && (
        <div style={{ 
          fontSize: '0.75rem',
          color: 'var(--text-secondary)',
          marginTop: '0.5rem'
        }}>
          Relevance: {(article.relevance_score * 100).toFixed(0)}%
        </div>
      )}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between',
        fontSize: '0.75rem',
        color: 'var(--text-secondary)',
        marginTop: '1rem'
      }}>
        {article.source && <span>{article.source}</span>}
        {article.published_date && (
          <span>{formatDate(article.published_date)}</span>
        )}
      </div>
      {article.article_url && (
        <a
          href={article.article_url}
          target="_blank"
          rel="noopener noreferrer"
          className="terminal-link"
          style={{ marginTop: '0.5rem', display: 'inline-block' }}
          onClick={(e) => e.stopPropagation()}
        >
          Read more →
        </a>
      )}
    </DashboardCard>
  );
};

export default NewsCard;

