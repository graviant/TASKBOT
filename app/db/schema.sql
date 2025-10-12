create table if not exists users (
  id          bigint primary key,        -- telegram user id
  username    varchar(64),
  full_name   varchar(128),
  is_admin    boolean not null default false,
  is_member   boolean not null default false,
  created_at  timestamp not null default now()
);

create table if not exists assignments (
  id                     serial primary key,
  author_id              bigint not null references users(id) on delete restrict,
  work_type              varchar(50) not null,
  deadline_at            timestamp null,
  project                varchar(100),
  customer               varchar(100),
  total_volume           numeric(12,2) not null,
  comment                text,
  published_chat_id      bigint,
  published_message_id   int,
  created_at             timestamp not null default now(),
  is_active              boolean not null default true
);

create table if not exists task_claims (
  id            serial primary key,
  assignment_id int not null references assignments(id) on delete cascade,
  executor_id   bigint not null references users(id) on delete restrict,
  volume        numeric(12,2) not null,
  done          boolean not null default false,
  created_at    timestamp not null default now()
);

create index if not exists ix_task_claims_assignment_id on task_claims(assignment_id);
create index if not exists ix_assignments_active on assignments(is_active, created_at desc);
