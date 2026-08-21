-- Create the research_reports table
create table public.research_reports (
  id uuid default gen_random_uuid() primary key,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  
  -- Input Data
  linkedin_url text,
  website text,
  
  -- Analysis Results (Markdown Content)
  sales_research_report text,
  lead_score_analysis text,
  user_profile_analysis text,
  website_analysis text,
  
  -- Metrics
  lead_score integer,
  project_urgency integer
);

-- Enable Row Level Security (RLS)
alter table public.research_reports enable row level security;

-- Create a policy to allow anyone to read/write for now (simulating public access for development)
-- In a real SaaS, you'd restrict this to authenticated users.
create policy "Allow public access"
on public.research_reports
for all
using (true)
with check (true);
