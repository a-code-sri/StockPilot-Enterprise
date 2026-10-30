// Tiny, safe Markdown renderer for AI output: paragraphs, bullet/numbered lists,
// **bold**, *italic* and `code`. Builds React elements (never innerHTML), so model
// output cannot inject HTML.

function inline(text, keyPrefix) {
  const parts = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*\s][^*]*\*)/g;
  let last = 0;
  let m;
  let i = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    const tok = m[0];
    const key = `${keyPrefix}-${i++}`;
    if (tok.startsWith("**")) parts.push(<strong key={key}>{tok.slice(2, -2)}</strong>);
    else if (tok.startsWith("`")) parts.push(<code key={key} className="text-indigo-300">{tok.slice(1, -1)}</code>);
    else parts.push(<em key={key}>{tok.slice(1, -1)}</em>);
    last = m.index + tok.length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

export default function Markdown({ text }) {
  const blocks = [];
  let list = null;

  const flush = () => {
    if (list) {
      const Tag = list.ordered ? "ol" : "ul";
      blocks.push(
        <Tag key={`l${blocks.length}`} className={`${list.ordered ? "list-decimal" : "list-disc"} pl-5 space-y-1`}>
          {list.items.map((it, i) => (
            <li key={i}>{inline(it, `li${blocks.length}-${i}`)}</li>
          ))}
        </Tag>
      );
      list = null;
    }
  };

  for (const raw of (text || "").split("\n")) {
    const line = raw.trim();
    const bullet = line.match(/^[-*•]\s+(.*)$/);
    const numbered = line.match(/^\d+[.)]\s+(.*)$/);
    if (bullet || numbered) {
      const ordered = Boolean(numbered);
      if (!list || list.ordered !== ordered) {
        flush();
        list = { ordered, items: [] };
      }
      list.items.push((bullet || numbered)[1]);
    } else if (!line) {
      flush();
    } else {
      flush();
      const heading = line.match(/^#{1,6}\s+(.*)$/);
      blocks.push(
        <p key={`p${blocks.length}`} className={heading ? "font-semibold text-gray-100" : ""}>
          {inline(heading ? heading[1] : line, `p${blocks.length}`)}
        </p>
      );
    }
  }
  flush();

  return <div className="space-y-2 text-sm leading-relaxed text-gray-200">{blocks}</div>;
}
