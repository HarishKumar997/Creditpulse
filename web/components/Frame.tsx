import Link from "next/link";

const LINKS = [
  ["Overview", "/"],
  ["Portfolio", "/portfolio"],
  ["Quality", "/quality"],
  ["Runs", "/runs"],
  ["Architecture", "/architecture"],
];

export function Frame({
  children,
  disclaimer,
}: {
  children: React.ReactNode;
  disclaimer: string;
}) {
  return (
    <>
      <a className="skip" href="#content">
        Skip to content
      </a>
      <p className="banner">{disclaimer}</p>
      <header className="top">
        <div>
          <p className="eyebrow">Local data platform</p>
          <p className="wordmark">CreditPulse</p>
        </div>
        <nav aria-label="Demo sections">
          {LINKS.map(([label, href]) => (
            <Link key={href} href={href}>
              {label}
            </Link>
          ))}
        </nav>
      </header>
      <main id="content">{children}</main>
    </>
  );
}
