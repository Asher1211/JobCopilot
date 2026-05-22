interface Props {
  number: string;
  title: string;
  description: string;
}

export function FeatureCard({ number, title, description }: Props) {
  return (
    <div className="card border-t-0 border-l-0 p-8 hover:!bg-black hover:!text-white transition-colors group">
      <span className="font-[family-name:var(--font-mono)] text-[13px] text-[var(--color-text-secondary)] group-hover:!text-white mb-4 block">
        {number}
      </span>
      <h4 className="mb-3 group-hover:!text-white">{title}</h4>
      <p className="text-[15px] leading-relaxed text-[var(--color-text-secondary)] group-hover:!text-white">
        {description}
      </p>
    </div>
  );
}
