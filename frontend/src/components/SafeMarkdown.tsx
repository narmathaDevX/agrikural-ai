import React from 'react';

interface SafeMarkdownProps {
  content: string;
  className?: string;
}

interface InlineToken {
  type: 'text' | 'bold' | 'italic' | 'bold_italic' | 'code' | 'link';
  text?: string;
  label?: string;
  url?: string;
}

type BlockToken =
  | { type: 'heading'; level: number; text: string }
  | { type: 'bullet_list'; items: string[] }
  | { type: 'ordered_list'; items: string[] }
  | { type: 'blockquote'; lines: string[] }
  | { type: 'code_block'; lang: string; code: string }
  | { type: 'hr' }
  | { type: 'paragraph'; lines: string[] };

/**
 * Validates URLs to prevent XSS through javascript: or data: URIs.
 * Only http, https, and mailto protocols are permitted.
 */
function isSafeUrl(url: string): boolean {
  try {
    const trimmed = url.trim().toLowerCase();
    if (trimmed.startsWith('javascript:') || trimmed.startsWith('data:') || trimmed.startsWith('vbscript:')) {
      return false;
    }
    return /^https?:\/\//i.test(trimmed) || /^mailto:/i.test(trimmed);
  } catch {
    return false;
  }
}

/**
 * Tokenizes a single line of text into inline formatting tokens.
 * Supports bold, italic, bold-italic, inline code, links, and plain text.
 */
function tokenizeInline(text: string): InlineToken[] {
  if (!text) return [];

  // Match:
  // 1. Bold-Italic: ***text*** or ___text___
  // 2. Bold: **text** or __text__
  // 3. Italic: *text* or _text_
  // 4. Inline code: `text`
  // 5. Links: [label](url)
  const pattern = /(\*\*\*(?!\s)[\s\S]+?(?<!\s)\*\*\*|___(?!\s)[\s\S]+?(?<!\s)___|\*\*(?!\s)[\s\S]+?(?<!\s)\*\*|__(?!\s)[\s\S]+?(?<!\s)__|\*(?!\s)[^*\n]+?(?<!\s)\*|_(?!\s)[^_\n]+?(?<!\s)_|`[^`\n]+`|\[[^\]\n]+\]\([^)\n]+\))/g;

  const rawParts = text.split(pattern);
  const tokens: InlineToken[] = [];

  for (let i = 0; i < rawParts.length; i++) {
    const part = rawParts[i];
    if (!part) continue;

    if (
      (part.startsWith('***') && part.endsWith('***') && part.length >= 6) ||
      (part.startsWith('___') && part.endsWith('___') && part.length >= 6)
    ) {
      tokens.push({ type: 'bold_italic', text: part.slice(3, -3) });
    } else if (
      (part.startsWith('**') && part.endsWith('**') && part.length >= 4) ||
      (part.startsWith('__') && part.endsWith('__') && part.length >= 4)
    ) {
      tokens.push({ type: 'bold', text: part.slice(2, -2) });
    } else if (
      (part.startsWith('*') && part.endsWith('*') && part.length >= 2) ||
      (part.startsWith('_') && part.endsWith('_') && part.length >= 2)
    ) {
      tokens.push({ type: 'italic', text: part.slice(1, -1) });
    } else if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
      tokens.push({ type: 'code', text: part.slice(1, -1) });
    } else if (part.startsWith('[') && part.includes('](') && part.endsWith(')')) {
      const match = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      if (match) {
        tokens.push({ type: 'link', label: match[1], url: match[2] });
      } else {
        tokens.push({ type: 'text', text: part });
      }
    } else {
      tokens.push({ type: 'text', text: part });
    }
  }

  return tokens;
}

/**
 * Safely renders inline tokens into React virtual DOM elements.
 * JSX automatically escapes all text nodes, guaranteeing complete immunity to XSS.
 */
function renderInline(text: string): React.ReactNode {
  const tokens = tokenizeInline(text);

  return tokens.map((token, index) => {
    switch (token.type) {
      case 'bold':
        return (
          <strong key={index} className="font-semibold text-white">
            {token.text}
          </strong>
        );
      case 'italic':
        return (
          <em key={index} className="italic text-slate-200">
            {token.text}
          </em>
        );
      case 'bold_italic':
        return (
          <strong key={index} className="font-semibold text-white">
            <em className="italic">{token.text}</em>
          </strong>
        );
      case 'code':
        return (
          <code
            key={index}
            className="px-1.5 py-0.5 rounded bg-slate-800 text-emerald-300 font-mono text-[12px] border border-slate-700/60"
          >
            {token.text}
          </code>
        );
      case 'link':
        if (token.url && isSafeUrl(token.url)) {
          return (
            <a
              key={index}
              href={token.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-emerald-400 hover:text-emerald-300 underline underline-offset-2 transition-colors"
            >
              {token.label}
            </a>
          );
        }
        // Fallback for dangerous or unparseable URLs: render as safe plain text
        return <span key={index}>{token.label || token.url}</span>;
      case 'text':
      default:
        return <React.Fragment key={index}>{token.text}</React.Fragment>;
    }
  });
}

/**
 * Parses markdown text into high-level structural blocks.
 */
function parseBlocks(markdown: string): BlockToken[] {
  if (!markdown) return [];

  const lines = markdown.split(/\r?\n/);
  const blocks: BlockToken[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // 1. Code Fence (```lang ... ```)
    if (line.trim().startsWith('```')) {
      const lang = line.trim().slice(3).trim();
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      i++; // consume closing fence
      blocks.push({
        type: 'code_block',
        lang,
        code: codeLines.join('\n'),
      });
      continue;
    }

    // 2. Horizontal Rules: --- or *** or ___
    if (/^(\-{3,}|\*{3,}|_{3,})$/.test(line.trim())) {
      blocks.push({ type: 'hr' });
      i++;
      continue;
    }

    // 3. Headings: # H1 through ###### H6
    const headingMatch = line.match(/^(#{1,6})\s+(.+)$/);
    if (headingMatch) {
      blocks.push({
        type: 'heading',
        level: headingMatch[1].length,
        text: headingMatch[2].trim(),
      });
      i++;
      continue;
    }

    // 4. Blockquotes: > quote line
    if (/^>\s*/.test(line)) {
      const quoteLines: string[] = [];
      while (i < lines.length && /^>\s*/.test(lines[i])) {
        quoteLines.push(lines[i].replace(/^>\s*/, ''));
        i++;
      }
      blocks.push({
        type: 'blockquote',
        lines: quoteLines,
      });
      continue;
    }

    // 5. Bullet Lists: lines beginning with -, *, +, or •
    if (/^\s*[-*+•]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*[-*+•]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*[-*+•]\s+/, '').trim());
        i++;
      }
      blocks.push({
        type: 'bullet_list',
        items,
      });
      continue;
    }

    // 6. Ordered Lists: lines beginning with 1. , 2. , etc.
    if (/^\s*\d+\.\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*\d+\.\s+/, '').trim());
        i++;
      }
      blocks.push({
        type: 'ordered_list',
        items,
      });
      continue;
    }

    // 7. Empty whitespace lines
    if (!line.trim()) {
      i++;
      continue;
    }

    // 8. Paragraphs: consecutive non-empty lines until next special block or empty line
    const paraLines: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() &&
      !lines[i].trim().startsWith('```') &&
      !/^(\-{3,}|\*{3,}|_{3,})$/.test(lines[i].trim()) &&
      !/^(#{1,6})\s+(.+)$/.test(lines[i]) &&
      !/^>\s*/.test(lines[i]) &&
      !/^\s*[-*+•]\s+/.test(lines[i]) &&
      !/^\s*\d+\.\s+/.test(lines[i])
    ) {
      paraLines.push(lines[i]);
      i++;
    }

    if (paraLines.length > 0) {
      blocks.push({
        type: 'paragraph',
        lines: paraLines,
      });
    }
  }

  return blocks;
}

/**
 * Safe, robust React Markdown renderer.
 * Eliminates raw Markdown syntax while sanitizing content and preserving formatting.
 */
export const SafeMarkdown: React.FC<SafeMarkdownProps> = ({ content, className = '' }) => {
  if (!content) return null;

  const blocks = parseBlocks(content);

  return (
    <div className={`space-y-2 text-sm leading-relaxed ${className}`}>
      {blocks.map((block, bIdx) => {
        switch (block.type) {
          case 'heading': {
            if (block.level === 1) {
              return (
                <h1
                  key={bIdx}
                  className="text-base font-bold text-white mt-3 mb-1 border-b border-slate-800 pb-1"
                >
                  {renderInline(block.text)}
                </h1>
              );
            }
            if (block.level === 2) {
              return (
                <h2
                  key={bIdx}
                  className="text-sm font-bold text-emerald-400 mt-2.5 mb-1"
                >
                  {renderInline(block.text)}
                </h2>
              );
            }
            if (block.level === 3) {
              return (
                <h3
                  key={bIdx}
                  className="text-xs font-semibold text-emerald-300 mt-2 mb-0.5 uppercase tracking-wide"
                >
                  {renderInline(block.text)}
                </h3>
              );
            }
            return (
              <h4
                key={bIdx}
                className="text-xs font-semibold text-slate-200 mt-1.5 mb-0.5"
              >
                {renderInline(block.text)}
              </h4>
            );
          }

          case 'bullet_list':
            return (
              <ul key={bIdx} className="list-disc pl-5 space-y-1 my-1.5 text-slate-200">
                {block.items.map((item, iIdx) => (
                  <li key={iIdx} className="leading-relaxed">
                    {renderInline(item)}
                  </li>
                ))}
              </ul>
            );

          case 'ordered_list':
            return (
              <ol key={bIdx} className="list-decimal pl-5 space-y-1 my-1.5 text-slate-200">
                {block.items.map((item, iIdx) => (
                  <li key={iIdx} className="leading-relaxed">
                    {renderInline(item)}
                  </li>
                ))}
              </ol>
            );

          case 'blockquote':
            return (
              <blockquote
                key={bIdx}
                className="border-l-2 border-emerald-500/80 bg-slate-950/60 pl-3 py-1.5 my-1.5 rounded-r text-slate-300 text-xs italic"
              >
                {block.lines.map((line, lIdx) => (
                  <React.Fragment key={lIdx}>
                    {renderInline(line)}
                    {lIdx < block.lines.length - 1 && <br />}
                  </React.Fragment>
                ))}
              </blockquote>
            );

          case 'code_block':
            return (
              <pre
                key={bIdx}
                className="my-2 p-3 rounded-lg bg-slate-950 border border-slate-800 font-mono text-xs text-emerald-300 overflow-x-auto"
              >
                <code>{block.code}</code>
              </pre>
            );

          case 'hr':
            return <hr key={bIdx} className="my-2.5 border-slate-800" />;

          case 'paragraph':
            return (
              <p key={bIdx} className="text-slate-100 leading-relaxed my-1">
                {block.lines.map((line, lIdx) => (
                  <React.Fragment key={lIdx}>
                    {renderInline(line)}
                    {lIdx < block.lines.length - 1 && <br />}
                  </React.Fragment>
                ))}
              </p>
            );

          default:
            return null;
        }
      })}
    </div>
  );
};

export default SafeMarkdown;
