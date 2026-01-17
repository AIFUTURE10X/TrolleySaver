import { Link, Outlet } from 'react-router-dom';

export function Layout() {
  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Header - full width */}
      <header className="bg-white shadow-sm border-b">
        <div className="px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link to="/" className="flex items-center gap-2">
              <span className="text-2xl">🛒</span>
              <span className="font-bold text-xl text-gray-900">
                Trolley Saver
              </span>
            </Link>

            <nav className="flex items-center gap-6">
              <Link
                to="/"
                className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
              >
                Specials
              </Link>
              <Link
                to="/staples"
                className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
              >
                Staples
              </Link>
              <Link
                to="/compare"
                className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
              >
                Compare
              </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Main content - full width */}
      <main className="flex-1 w-full px-4 sm:px-6 lg:px-8 py-6">
        <Outlet />
      </main>

      {/* Footer - full width */}
      <footer className="bg-white border-t py-6">
        <div className="px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-sm text-gray-500">
              Your smart shopping companion for Australian supermarkets
            </p>
            <div className="flex gap-6">
              <span className="text-sm font-medium text-[#00A651]">Woolworths</span>
              <span className="text-sm font-medium text-[#E01A22]">Coles</span>
              <span className="text-sm font-medium text-[#00448C]">ALDI</span>
              <span className="text-sm font-medium text-[#FF6B00]">IGA</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
