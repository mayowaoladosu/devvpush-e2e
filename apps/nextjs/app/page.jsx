const release = "release-v1";

export default function Page() {
  return (
    <main data-fixture="nextjs" data-release={release}>
      <h1>devvpush Next.js E2E</h1>
      <p>{release}</p>
    </main>
  );
}
