import { Search } from 'lucide-react';
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
  const limit = filters.limit ?? 50;
  const offset = filters.offset ?? 0;
  const nextOffset = Math.min(offset + limit, Math.max(total - limit, 0));
  const previousOffset = Math.max(offset - limit, 0);
  return (
    <section className="panel wide-panel">
      <div className="panel-header">
        <h2>Posts Explorer</h2>
        <span className="pill">{total} rows</span>
      </div>
      <div className="facet-strip">
        {(facets.platforms ?? []).slice(0, 4).map((facet) => (
          <span key={String(facet.value)}>{facet.value ?? '-'}: {facet.count}</span>
        ))}
      </div>
      <div className="filters">
        <label>
          <span>Platform</span>
          <select
            value={filters.platform ?? ''}
            onChange={(event) => onFiltersChange({ ...filters, platform: event.target.value || undefined })}
          >
            <option value="">All</option>
            <option value="dcard">Dcard</option>
            <option value="ptt">PTT</option>
            <option value="news">News</option>
          </select>
        </label>
        <label>
          <span>Keyword</span>
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
              <th>Platform</th>
              <th>Board</th>
              <th>Title</th>
              <th>Comments</th>
              <th>Published</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5}>Loading posts...</td></tr>
            ) : posts.length === 0 ? (
              <tr><td colSpan={5}>No posts match the current filters.</td></tr>
            ) : (
              posts.map((post) => (
                <tr key={`${post.source}:${post.external_id}`}>
                  <td>{post.platform}</td>
                  <td>{post.board_or_forum ?? '-'}</td>
                  <td>
                    <button className="link-button" type="button" onClick={() => onSelectPost?.(post)}>
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
          Previous
        </button>
        <span>
          Showing {total ? offset + 1 : 0}-{Math.min(offset + posts.length, total)} of {total}
        </span>
        <button type="button" onClick={() => onPageChange(nextOffset)} disabled={offset + limit >= total || loading}>
          Next
        </button>
      </div>
    </section>
  );
}
