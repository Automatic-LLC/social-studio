-- Social Studio, first tables. Run once in Social Studio's own Supabase project:
-- Dashboard > SQL Editor > New query > paste this file > Run.

create table if not exists posts (
  id            bigint generated always as identity primary key,
  account       text not null,                       -- accounts/<name>.yaml, e.g. ur_dailydog
  kind          text not null check (kind in ('reel', 'image', 'carousel', 'story')),
  status        text not null default 'scheduled'
                check (status in ('draft', 'scheduled', 'publishing', 'posted', 'failed', 'killed', 'skipped', 'reserve')),
  post_at       timestamptz,                         -- null for reserve posts
  caption       text not null default '',
  media         jsonb not null default '[]',         -- [{"path": "ur_dailydog/20261101/ab12cd34.mp4"}, ...]
  source        text not null default 'own'
                check (source in ('own', 'submission', 'pexels', 'ai', 'contest')),
  credit        text,                                -- owner handle or "Pexels: <name>"
  is_ai         boolean not null default false,      -- true: Meta's AI label goes on
  qa_passed     boolean not null default false,      -- the publisher refuses posts without both checks
  caption_ok    boolean not null default false,
  collaborators text[] not null default '{}',
  to_facebook   boolean not null default true,
  batch_id      text,
  ig_container  text,
  ig_media_id   text,
  permalink     text,
  fb_video_id   text,
  fb_error      text,
  attempts      int not null default 0,
  last_error    text,
  created_at    timestamptz not null default now(),
  posted_at     timestamptz
);
create index if not exists posts_due on posts (status, post_at);
create index if not exists posts_account on posts (account, status);

create table if not exists post_log (
  id      bigint generated always as identity primary key,
  post_id bigint references posts (id) on delete cascade,
  at      timestamptz not null default now(),
  event   text not null,
  detail  jsonb not null default '{}'
);
create index if not exists post_log_post on post_log (post_id);

-- Row level security on with no policies: only the secret key (the publisher) can read or write.
alter table posts enable row level security;
alter table post_log enable row level security;

-- Public bucket Meta fetches post media from (files are deleted after posting).
insert into storage.buckets (id, name, public)
values ('media', 'media', true)
on conflict (id) do nothing;
