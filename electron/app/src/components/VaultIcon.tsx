import { motion } from "motion/react";

interface VaultIconProps {
  className?: string;
  isOpen?: boolean;
}

export function VaultIcon({ className = "h-6 w-6", isOpen = false }: VaultIconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      {/* Lock body */}
      <rect x="5" y="11" width="14" height="11" rx="2" ry="2" />

      {/* Keyhole */}
      <circle cx="12" cy="16" r="1" />
      <line x1="12" y1="17" x2="12" y2="19" />

      {/* Animated shackle */}
      <motion.path
        d={isOpen ? "M7 11V7a5 5 0 0 1 5 -5" : "M7 11V7a5 5 0 0 1 10 0v4"}
        initial={false}
        animate={{
          d: isOpen ? "M7 11V7a5 5 0 0 1 5 -5" : "M7 11V7a5 5 0 0 1 10 0v4"
        }}
        transition={{
          type: "spring",
          stiffness: 200,
          damping: 28
        }}
      />
    </svg>
  );
}
