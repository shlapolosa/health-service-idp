#!/usr/bin/env bash
# HARD-1 (#168): UNIFY-1 (#153) concurrency-safe push, bounded rebase-retry —
# heredoc lines 261-285 verbatim.
mscv_git_push_retry() {
# UNIFY-1 (#153, 2026-06-07) concurrency fix: in the monorepo-per-OAM world the
# AppContainerClaim emits ONE ApplicationClaim per webservice component, so N mscv
# Jobs now race the SAME shared repo. A bare `git push` is non-atomic: between our
# `git pull --rebase` above and the push another Job can land its commit, making
# our push a non-fast-forward (rejected). Retry: on rejection, fetch + rebase onto
# the new remote HEAD (our commit only touches microservices/$SERVICE_NAME so the
# rebase is conflict-free against sibling services) and push again. Bounded so a
# genuinely broken remote fails the Job instead of looping forever. Jittered sleep
# spreads out simultaneous retriers.
PUSH_OK=0
for attempt in $(seq 1 10); do
  if git push origin HEAD; then
    PUSH_OK=1
    echo "push succeeded on attempt $attempt"
    break
  fi
  echo "push rejected (attempt $attempt/10) - likely a concurrent sibling mscv push; fetching, rebasing, retrying"
  git fetch origin || true
  git pull --rebase origin HEAD || { echo "unexpected rebase conflict (services should be disjoint); aborting rebase"; git rebase --abort || true; }
  sleep $(( (RANDOM % 5) + 1 ))
done
if [ "$PUSH_OK" != "1" ]; then
  echo "ERROR: failed to push $SERVICE_NAME after 10 attempts"
  exit 1
fi
}
