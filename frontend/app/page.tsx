import { FeatureCard } from "@/components/feature-card";
import Link from "next/link";

export default function Home() {
  return (
    <>
      {/* Hero */}
      <section className="border-b-[3px] border-black px-6 py-[120px] md:px-12">
        <div className="mx-auto max-w-[900px]">
          <h1>
            AI Job
            <br />
            Co-Pilot
          </h1>
          <p className="mb-10 max-w-[600px] text-[20px] leading-relaxed text-[var(--color-text-secondary)]">
            From resume matching to mock interviews, AI eliminates
            information gaps in your job hunt. Stop spraying resumes &mdash;
            start preparing with precision.
          </p>
          <div className="flex flex-wrap gap-4">
            <Link href="/analysis" className="btn btn-primary btn-lg">
              Start Analysis
            </Link>
            <Link href="/auth/login" className="btn btn-secondary btn-lg">
              Sign In / Register
            </Link>
          </div>
        </div>
      </section>

      {/* Feature Cards */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
        <FeatureCard
          number="01"
          title="Resume × JD Matching"
          description="Upload your resume and paste a job description. AI analyzes skill match, identifies gaps, and delivers actionable improvement suggestions."
        />
        <FeatureCard
          number="02"
          title="AI Mock Interview"
          description="Personalized interview questions generated from target roles. Multi-turn dialogue with real-time feedback to structure your responses."
        />
        <FeatureCard
          number="03"
          title="Company Research"
          description="One-click search for tech stack preferences, interview style, and salary ranges of your target companies."
        />
        <FeatureCard
          number="04"
          title="Resume Optimizer"
          description="Rewrite project descriptions and skill highlights tailored to a specific JD. Compare multiple versions side by side."
        />
        <FeatureCard
          number="05"
          title="RAG Question Bank"
          description="Curated interview questions tagged by role, difficulty, and tech stack. Precise retrieval for the most relevant practice problems."
        />
        <FeatureCard
          number="06"
          title="Study Roadmap"
          description="Auto-generate a structured learning plan based on identified weaknesses, with timeline and resource recommendations."
        />
      </section>

      {/* Bottom CTA */}
      <section className="border-t-[3px] border-black px-6 py-20 text-center">
        <h3 className="mb-4">Ready to start?</h3>
        <p className="mb-8 text-lg text-[var(--color-text-secondary)]">
          No download required. Open in your browser and go.
        </p>
        <Link href="/analysis" className="btn btn-primary btn-lg">
          Start Free
        </Link>
      </section>
    </>
  );
}
