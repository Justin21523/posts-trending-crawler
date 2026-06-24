import { Search } from 'lucide-react';
import type { PostFilters } from '../api/client';
import type { PostResponse } from '../api/types';

type PostsExplorerProps = {
  posts: PostResponse[];
  filters: PostFilters;
  loading: boolean;
  onFiltersChange: (filters: PostFilters) => void;
  onSelectPost?: (post: PostResponse) => void;
};

export function PostsExplorer({ posts, filters, loading, onFiltersChange, onSelectPost }: PostsExplorerProps) {
  return (
    <section className="panel wide-panel">
      <div className="panel-header">
        <h2>Posts Explorer</h2>
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
    </section>
  );
}
