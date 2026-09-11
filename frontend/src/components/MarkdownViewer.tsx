type MarkdownViewerProps = {
  content: string;
};

export function MarkdownViewer({ content }: MarkdownViewerProps) {
  return <pre className="content-block large-block">{content || "No Markdown export available."}</pre>;
}
