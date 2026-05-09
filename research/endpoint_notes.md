# Dcard API Endpoint Research Notes

## Known Endpoints (Based on Community Research)

### Forum Posts Listing
- **URL**: `https://api.dcard.tw/service/api/v2/forums/{forum_alias}/posts`
- **Method**: GET
- **Parameters**:
  - `popular`: `true` or `false` - Whether to fetch popular posts
  - `before`: Post ID - Fetch posts before this ID (pagination)
  - `limit`: Number - Number of posts to return (default ~30)
- **Response**: Array of post objects with basic metadata

### Post Detail
- **URL**: `https://api.dcard.tw/service/api/v2/posts/{post_id}`
- **Method**: GET
- **Response**: Single post object with full content

### Post Comments (NOT USED)
- **URL**: `https://api.dcard.tw/service/api/v2/posts/{post_id}/comments`
- **Note**: We intentionally do NOT fetch comments per project requirements

## Observed Post Object Fields

### Listing Response
```json
{
  "id": 123456,
  "title": "Post title",
  "excerpt": "Brief excerpt...",
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T13:00:00Z",
  "comment_count": 10,
  "like_count": 50,
  "school": "National Taiwan University",
  "department": "Computer Science",
  "anonymous_school": false,
  "anonymous_department": false,
  "with_nickname": false,
  "nsfw": false,
  "gender": "F",
  "topics": [{"name": "news", "id": 1}]
}
```

### Detail Response
Includes all listing fields plus:
```json
{
  "content": "Full post content...",
  "forum_alias": "trending",
  "forum_name": "時事板",
  "media": [
    {
      "type": "image",
      "url": "https://img.dcardcdn.io/...",
      "width": 800,
      "height": 600
    }
  ],
  "preview": "Preview image URL"
}
```

## Pagination Strategy

Dcard uses cursor-based pagination with `before` parameter:
1. First request: no `before` parameter (gets latest posts)
2. Subsequent requests: use last post's ID as `before` value
3. Continue until empty array returned

## Rate Limiting Observations

- No official rate limit published
- Community reports suggest ~2-3 requests/second is safe
- 429 responses indicate rate limiting
- Aggressive scraping may result in temporary blocks

## Robots.txt Analysis

Dcard's `robots.txt` currently only blocks:
- `/emails/activate`

The trending forum and API endpoints are NOT explicitly disallowed.

## Notes

- Endpoints may change without notice
- Always implement fallback/discovery mechanism
- Monitor for API structure changes
- Store raw_json for future schema migrations

## References

- Community blog: https://blog.jiatool.com/posts/dcard_api_v2/
- Dcard trending: https://www.dcard.tw/f/trending
- Dcard robots.txt: https://www.dcard.tw/robots.txt
