---
source_url: https://techsynth.tech/blog/semantic-search-postgres-pgvector-supabase/
fetched_at: 2026-04-27T22:15:12Z
category: technical
title: 'Postgres Semantic Search: pgvector Guide (Supabase)'
---

# Postgres Semantic Search: pgvector Guide (Supabase)

Join 500+ Devs Scaling Supabase Right Now
Get exclusive insights and proven strategies for scaling serverless applications with Supabase.
The standard PostgreSQL Full Text Search (
tsvector
) is powerful, but it has a flaw: it relies on
exact
keyword matching. If a user searches for “automobile” but your database only contains “car,” standard search returns nothing.
Enter
Semantic Search
. By converting text into vectors (arrays of numbers representing meaning) and storing them in Postgres, we can find records that are
conceptually
similar, even if they don’t share a single word.
Here is how to implement this in Supabase using the
pgvector
extension.
Step 1: Enable the Extension
First, we need to enable
pgvector
in our Postgres instance. In the Supabase SQL editor, run:
create
extension
if
not
exists
vector
;
This unlocks the
vector
data type, which stores arrays of floating-point numbers efficiently.
Step 2: Define the Schema
We need a column to store the vector embeddings. If you are using OpenAI’s
text-embedding-3-small
model, the output dimension is 1536.
Option A: Create a new table from scratch:
create
table
documents
(
id
bigserial
primary key
,
content
text
,
embedding
vector
(
1536
)
-- Matches OpenAI embedding size
);
Option B: Add to an existing table:
alter
table
blog_posts
add
column embedding
vector
(
1536
);
Step 3: Indexing for Performance
Searching through thousands of vectors can be slow. We can speed this up using an HNSW (Hierarchical Navigable Small World) index, which is highly efficient for approximate nearest neighbor search.
create
index
on
documents
using
hnsw (embedding vector_cosine_ops);
This index enables fast similarity searches even with millions of vectors. The
vector_cosine_ops
operator class optimizes for cosine distance, which is the standard metric for semantic similarity.
Step 4: Generate Embeddings
We need to convert our blog post content into vectors. This is typically done via an Edge Function that calls OpenAI’s API:
import
{ OpenAI }
from
"npm:openai@4"
;
const
openai
=
new
OpenAI
({
apiKey: Deno.env.
get
(
"OPENAI_API_KEY"
),
});
const
response
=
await
openai.embeddings.
create
({
model:
"text-embedding-3-small"
,
input: blogPostContent,
});
const
embedding
=
response.data[
0
].embedding;
Step 5: Store the Embeddings
Insert the embedding alongside your post:
update
blog_posts
set
embedding
=
$
1
where
id
=
$
2
;
For new records, you can include the embedding during insertion:
insert into
documents (content, embedding)
values
($
1
, $
2
);
Step 6: Query by Similarity (Cosine Distance)
Now the magic happens. When a user searches, we convert their query into an embedding and find the closest matches.
To find similar content, we compare the user’s search query vector against our stored document vectors. We want the items with the closest distance.
In Postgres, the
<=>
operator represents
cosine distance
. We wrap this in a Remote Procedure Call (RPC) for easy access via the Supabase JS Client:
create or replace
function
match_documents
(
query_embedding
vector
(
1536
),
match_threshold
float
,
match_count
int
)
returns
setof documents
language
plpgsql
as
$$
begin
return
query
select
*
from
documents
where
1
-
(
documents
.
embedding
<=>
query_embedding)
>
match_threshold
order by
documents
.
embedding
<=>
query_embedding
limit
match_count;
end
;
$$;
Now you can call this from your frontend:
const
queryEmbedding
=
await
getEmbedding
(userSearchQuery);
const
{
data
,
error
}
=
await
supabase.
rpc
(
'match_documents'
, {
query_embedding: queryEmbedding,
match_threshold:
0.78
,
match_count:
10
});
The function returns documents ordered by similarity, with the most relevant results first.
Performance Considerations
Cost:
OpenAI charges per token. Cache embeddings aggressively.
Latency:
Pre-compute embeddings during content creation, not at query time.
Hybrid Search:
Combine semantic search with traditional filters (date, category) for best results.
Conclusion
Semantic search transforms user experience by understanding
intent
, not just keywords. With
pgvector
, Postgres becomes a vector database without needing a separate service.
In production, consider implementing incremental embedding updates and monitoring vector index performance as your dataset grows.
Join 500+ Devs Scaling Supabase Right Now
Get exclusive insights and proven strategies for scaling serverless applications with Supabase.
Tags
postgres
ai-engineering
supabase
machine-learning
pgvector
semantic-search
Share this article
Twitter
LinkedIn
Facebook
Comments
Comments section will be integrated here. Popular options include Disqus, Utterances, or custom comment systems.