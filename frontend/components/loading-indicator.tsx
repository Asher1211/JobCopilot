interface Props {
  text: string;
}

export function LoadingIndicator({ text }: Props) {
  return (
    <div className="flex items-center gap-3">
      <div className="w-4 h-4 border-[3px] border-black animate-pulse" />
      <span className="label">{text}</span>
    </div>
  );
}
