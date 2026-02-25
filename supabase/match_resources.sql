create extension if not exists vector;

drop function if exists match_resources(vector, integer, double precision, text[], text[]);

create function match_resources(
    query_embedding vector(1536),
    match_count integer default 10,
    match_threshold double precision default 1.0,
    filter_tags text[] default null,
    filter_categories text[] default null
)
returns table (
    id resources.id%TYPE,
    title resources.title%TYPE,
    url resources.url%TYPE,
    notes resources.notes%TYPE,
    tags resources.tags%TYPE,
    categories resources.categories%TYPE,
    created_at resources.created_at%TYPE
)
language plpgsql as $$
begin
  return query
  select r.id, r.title, r.url, r.notes, r.tags, r.categories, r.created_at
  from resources r
  where r.embeddings_vector is not null
    and (filter_tags is null or r.tags = any(filter_tags))
    and (filter_categories is null or r.categories = any(filter_categories))
    and (r.embeddings_vector <=> query_embedding) <= match_threshold
  order by r.embeddings_vector <=> query_embedding
  limit match_count;
end;
$$;
