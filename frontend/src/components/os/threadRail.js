/** Thread-rail grouping for repeated scheduled runs. */

export function threadTitle(thread) {
  const title = (thread?.title || "").trim();
  return title || "Untitled task";
}

/**
 * Scheduled runs of the same task share a prefix. Group on that prefix so a
 * newly stored full title still collapses with an older shortened one.
 */
export function scheduledGroupKey(title) {
  const text = (title || "").trim().replace(/\s+/g, " ");
  const match = text.match(/^scheduled:\s*(.*)$/i);
  if (!match) return null;
  // Older runs stored only the first 60 characters of the prompt.
  return match[1].slice(0, 60).toLowerCase();
}

export function filterThreads(threads, query) {
  const q = (query || "").trim().toLowerCase();
  if (!q) return threads || [];
  return (threads || []).filter((thread) =>
    threadTitle(thread).toLowerCase().includes(q),
  );
}

export function groupThreads(threads) {
  const groups = [];
  const byKey = new Map();
  for (const thread of threads || []) {
    const title = threadTitle(thread);
    const key = scheduledGroupKey(title);
    if (!key) {
      groups.push({ kind: "thread", thread, title });
      continue;
    }
    let group = byKey.get(key);
    if (!group) {
      group = { kind: "group", key, title, threads: [] };
      byKey.set(key, group);
      groups.push(group);
    }
    group.threads.push(thread);
    if (title.length > group.title.length) group.title = title;
  }
  return groups;
}
