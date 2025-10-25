import { useState, useEffect } from "react";

interface TypingMessageProps {
  content: string;
  onComplete?: () => void;
  typingSpeed?: number;
}

export function TypingMessage({ content, onComplete, typingSpeed = 20 }: TypingMessageProps) {
  const [displayedContent, setDisplayedContent] = useState("");
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    if (currentIndex < content.length) {
      const timeout = setTimeout(() => {
        setDisplayedContent((prev) => prev + content[currentIndex]);
        setCurrentIndex((prev) => prev + 1);
      }, typingSpeed);

      return () => clearTimeout(timeout);
    } else if (currentIndex === content.length && !isComplete) {
      setIsComplete(true);
      onComplete?.();
    }
  }, [currentIndex, content, typingSpeed, isComplete, onComplete]);

  return (
    <span className="whitespace-pre-wrap text-foreground">
      {displayedContent}
      {!isComplete && (
        <span className="inline-block w-[2px] h-[1em] bg-current ml-[1px] animate-blink" />
      )}
    </span>
  );
}
