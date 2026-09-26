import { Link } from '@/i18n/navigation';

export default function ResearchPage() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Research Lab</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Link href="/research/leakage-lab" className="block p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:bg-gray-50 transition-colors">
          <h5 className="mb-2 text-xl font-bold tracking-tight text-gray-900">Leakage Lab</h5>
          <p className="font-normal text-gray-700">Compare predictions against actual subsequent prints using scatter plots.</p>
        </Link>
      </div>
    </div>
  );
}
