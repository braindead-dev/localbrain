import Image from "next/image";

export default function Home() {
  return (
    <div className="min-h-screen w-full bg-zinc-50 font-sans dark:bg-black">
      <main className="min-h-screen w-full bg-white dark:bg-black">
        <div className="flex min-h-screen w-full items-center justify-center">
          <div className="flex flex-col items-center gap-6 text-center">
            <Image
              className="dark:invert"
              src="/next.svg"
              alt="Next.js logo"
              width={180}
              height={38}
              priority
            />
            <h1 className="text-4xl font-bold leading-10 tracking-tight text-black dark:text-zinc-50">
              Welcome to LocalBrain
            </h1>
            <p className="max-w-md text-lg leading-8 text-zinc-600 dark:text-zinc-400">
              Your Next.js app is now running inside Electron! 🎉
            </p>
            <div className="flex flex-col gap-4 text-base font-medium sm:flex-row">
              <button className="flex h-12 items-center justify-center gap-2 rounded-full bg-blue-600 px-8 text-white transition-colors hover:bg-blue-700">
                Get Started
              </button>
              <button className="flex h-12 items-center justify-center rounded-full border border-solid border-black/[.08] px-8 transition-colors hover:border-transparent hover:bg-black/[.04] dark:border-white/[.145] dark:hover:bg-[#1a1a1a]">
                Documentation
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
