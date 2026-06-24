import { Search } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { PostFilters } from '../api/client';
import type { PostResponse } from '../api/types';

type PostsExplorerProps = {
  posts: PostResponse[];
  total: number;
  facets: Record<string, Array<{ value: string | null; count: number }>>;
  filters: PostFilters;
  loading: boolean;
  onFiltersChange: (filters: PostFilters) => void;
  onPageChange: (offset: number) => void;
  onSelectPost?: (post: PostResponse) => void;
};

export function PostsExplorer({
  posts,
  total,
  facets,
  filters,
  loading,
  onFiltersChange,
  onPageChange,
  onSelectPost,
}: PostsExplorerProps) {
  const { t } = useTranslation();
  const limit = filters.limit ?? 50;
  const offset = filters.offset ?? 0;
  const nextOffset = Math.min(offset + limit, Math.max(total - limit, 0));
  const previousOffset = Math.max(offset - limit, 0);
  return (
    <section className="panel wide-panel">
      <div className="panel-header">
        <h2>{t('explorer.title')}</h2>
        <span className="pill">{total} {t('common.rows')}</span>
      </div>
      <div className="facet-strip">
        {(facets.platforms ?? []).slice(0, 4).map((facet) => (
          <span key={String(facet.value)}>{facet.value ?? '-'}: {facet.count}</span>
        ))}
      </div>
      <div className="filters">
        <label>
          <span>{t('common.platform')}</span>
          <select
            value={filters.platform ?? ''}
            onChange={(event) => onFiltersChange({ ...filters, platform: event.target.value || undefined })}
          >
            <option value="">{t('explorer.all')}</option>
            <option value="dcard">Dcard</option>
            <option value="ptt">PTT</option>
            <option value="news">News</option>
          </select>
        </label>
        <label>
          <span>{t('explorer.search')}</span>
          <div className="search-input">
            <Search size={15} />
            <input
              value={filters.keyword ?? ''}
              onChange={(event) => onFiltersChange({ ...filters, keyword: event.target.value || undefined })}
              placeholder="AI, 台灣, 工作"
            />
          </div>
        </label>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>{t('common.platform')}</th>
              <th>{t('common.board')}</th>
              <th>{t('common.title')}</th>
              <th>{t('common.comments')}</th>
              <th>{t('common.published')}</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5}>{t('explorer.loading')}</td></tr>
            ) : posts.length === 0 ? (
              <tr><td colSpan={5}>{t('explorer.empty')}</td></tr>
            ) : (
              posts.map((post) => (
                <tr
                  className="clickable-row interactive-row"
                  key={`${post.source}:${post.external_id}`}
                  role="button"
                  tabIndex={0}
                  onClick={() => onSelectPost?.(post)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault();
                      onSelectPost?.(post);
                    }
                  }}
                >
                  <td>{post.platform}</td>
                  <td>{post.board_or_forum ?? '-'}</td>
                  <td>
                    <button
                      className="link-button"
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        onSelectPost?.(post);
                      }}
                    >
                      {post.title}
                    </button>
                    <p>{post.excerpt || post.content || ''}</p>
                  </td>
                  <td>{post.comment_count}</td>
                  <td>{post.published_at ?? post.created_at ?? '-'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <div className="pagination-row">
        <button type="button" onClick={() => onPageChange(previousOffset)} disabled={offset === 0 || loading}>
          {t('explorer.previous')}
        </button>
        <span>
          {t('explorer.showing', { start: total ? offset + 1 : 0, end: Math.min(offset + posts.length, total), total })}
        </span>
        <button type="button" onClick={() => onPageChange(nextOffset)} disabled={offset + limit >= total || loading}>
          {t('explorer.next')}
        </button>
      </div>
    </section>
  );
}
