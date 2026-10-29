# Fintech Regulatory Radar: a short overview

## What it is

The Radar is a tool that keeps track of Indian fintech regulation and turns it into something a
lawyer can act on quickly. You tell it which areas you follow, it pulls together the recent
developments from the regulators, and for each one it gives you a plain summary, the sub-sectors it
affects, how big a deal it is, and a short list of what the affected businesses should do. If you
tell it about a particular client, it sorts the items so the ones that matter to that client come
first.

## Why I built it

Fintech in India is regulated by several bodies at once, and they move fast. RBI, SEBI, MeitY, NPCI
and others keep issuing circulars, directions and draft rules on things like digital lending,
payment aggregators, wallets, account aggregators and data protection. For a law firm that advises
fintech clients, staying on top of all of it is a real chore, and being the first to flag a change
to a client is part of how the firm earns its keep.

I wanted to build the thing I would want in that seat: a single place that watches the regulators,
tells me what changed in normal language, and helps me work out who it affects and what they should
do. It is the kind of tool a fintech practice genuinely needs, rather than a demo that only looks
clever.

## What it does, in plain terms

- You choose the areas you care about, such as digital lending or payments, or leave it open to
  cover everything.
- It finds the recent developments and lays them out as cards, newest and most important first.
- Each card tells you which regulator, the date, whether it is final or still a draft, what changed,
  who has to do something, and what they should do.
- You can add a client's business, and it will mark the items that are relevant to them and push
  those to the top.
- In live mode it searches the web for current regulation and shows you the sources, so you can
  check anything before you rely on it.

## How it works, briefly

When you run a scan, the tool searches the web for recent regulatory developments in the areas you
picked, then turns those findings into a clean, structured list: a summary, the sectors, the impact
level, who must act and what to do. After that it scores each item, works out how relevant it is to
the client you named, sorts everything, and shows it. There is also a demo mode that uses a built-in
sample set, so the app works and can be shown without any setup or cost.

## What it is built with

It is a Streamlit app, which means the whole thing is one Python program with a web interface, and
it deploys to the free Streamlit Community Cloud in a few clicks. The regulatory research and the
summarising are done by a language model with live web search. It runs on an ordinary laptop.

## What it does not do

It is a monitoring aid, not a replacement for a lawyer. It helps you spot and understand changes
faster, but a qualified lawyer still has to read the actual regulation and advise on it. In live
mode it is only as current and accurate as what it can find on the web, so anything important should
be checked against the regulator's own notice.

## Where it could go next

A few natural next steps: saved client profiles so the firm can run the same scan for each client
on a schedule, email or Slack alerts when something high-impact appears, and a longer memory so the
Radar can show how a rule has changed over time rather than just the latest position.
