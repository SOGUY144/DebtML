import "./globals.css";
import Link from "next/link";
import { BarChart3, Activity, Layers, ActivitySquare, ServerCrash } from "lucide-react";

export const metadata = {
  title: "DTI ML — Policy Dashboard",
  description: "Household debt risk analysis dashboard for policy makers",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <div style={{ display: 'flex', minHeight: '100vh' }}>
          {/* Sidebar */}
          <aside style={{
            width: '260px',
            background: 'var(--sidebar-bg)',
            borderRight: '1px solid var(--card-border)',
            padding: '2rem 1.5rem',
            display: 'flex',
            flexDirection: 'column'
          }}>
            <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
              <h1 className="outfit" style={{ fontSize: '2rem', marginBottom: '0.25rem' }}>
                DTI <span style={{ color: 'var(--accent)' }}>ML</span>
              </h1>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', letterSpacing: '1px', textTransform: 'uppercase' }}>
                Command Center
              </p>
            </div>

            <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', flex: 1 }}>
              <NavLink href="/" icon={<ActivitySquare size={20} />} label="Overview" />
              <NavLink href="/deep-dive" icon={<BarChart3 size={20} />} label="Deep-Dive" />
              <NavLink href="/models" icon={<Layers size={20} />} label="Models" />
              <NavLink href="/simulate" icon={<Activity size={20} />} label="Simulate" />
            </nav>
            
            <div style={{
              marginTop: 'auto',
              padding: '1rem',
              background: 'rgba(46, 213, 115, 0.1)',
              borderRadius: '8px',
              border: '1px solid rgba(46, 213, 115, 0.3)',
              textAlign: 'center',
              fontSize: '0.8rem',
              color: 'var(--stable)'
            }}>
              SYS.STATUS: ONLINE
            </div>
          </aside>

          {/* Main Content */}
          <main style={{ flex: 1, padding: '2rem 3rem', height: '100vh', overflowY: 'auto' }}>
            <header style={{ marginBottom: '2.5rem', animation: 'fadeIn 0.8s ease-out' }}>
              <h1 className="outfit" style={{ fontSize: '2.4rem', marginBottom: '0.5rem' }}>
                Policy Dashboard
              </h1>
              <p style={{ color: 'var(--text-secondary)', fontSize: '1.05rem', maxWidth: '650px' }}>
                วิเคราะห์ความเสี่ยงหนี้ครัวเรือนระดับจังหวัด สำหรับนักวิเคราะห์นโยบาย
              </p>
            </header>
            
            <div className="fade-in">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}

function NavLink({ href, icon, label }) {
  // Normally we'd use usePathname for active state, but keeping it simple for now
  return (
    <Link href={href} className="nav-link">
      {icon}
      <span>{label}</span>
    </Link>
  );
}
