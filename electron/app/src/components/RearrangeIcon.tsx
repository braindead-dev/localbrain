interface RearrangeIconProps {
  className?: string;
}

export function RearrangeIcon({ className }: RearrangeIconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <rect x="3" y="5" width="18" height="3" fill="currentColor" />
      <rect x="3" y="10.5" width="18" height="3" fill="currentColor" />
      <rect x="3" y="16" width="18" height="3" fill="currentColor" />
    </svg>
  );
}
