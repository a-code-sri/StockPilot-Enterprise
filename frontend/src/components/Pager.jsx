import { buttonClass } from "./ui";

/** Offset pagination controls driven by the API's X-Total-Count header. */
export default function Pager({ offset, limit, total, onChange }) {
  if (total <= limit) return null;
  const page = Math.floor(offset / limit) + 1;
  const pages = Math.max(1, Math.ceil(total / limit));
  return (
    <div className="flex items-center justify-end gap-3 mt-4 text-sm text-gray-400">
      <span>
        Page {page} of {pages} · {total} total
      </span>
      <button className={buttonClass.small} disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - limit))}>
        Previous
      </button>
      <button className={buttonClass.small} disabled={offset + limit >= total} onClick={() => onChange(offset + limit)}>
        Next
      </button>
    </div>
  );
}
