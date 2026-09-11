type MetadataViewerProps = {
  value: unknown;
};

export function MetadataViewer({ value }: MetadataViewerProps) {
  return <pre className="content-block large-block">{JSON.stringify(value, null, 2)}</pre>;
}
