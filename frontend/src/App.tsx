import { useEffect } from 'react'
import { AuthProvider, useAuth } from './context/AuthContext'
import { useRouter, matchPath } from './hooks/useRouter'
import AppLayout from './components/layout/AppLayout'
import Login from './components/auth/Login'
import Register from './components/auth/Register'
import ProjectList from './components/projects/ProjectList'
import CreateProject from './components/projects/CreateProject'
import ProjectDetail from './components/projects/ProjectDetail'

function AppContent() {
  const { user, isLoading } = useAuth()
  const { path, navigate } = useRouter()

  useEffect(() => {
    if (!isLoading && user && (path === '/' || path === '/login' || path === '/register')) {
      navigate('/projects', true)
    }
  }, [isLoading, user, path, navigate])

  useEffect(() => {
    if (!isLoading && !user && path !== '/' && path !== '/login' && path !== '/register') {
      navigate('/login', true)
    }
  }, [isLoading, user, path, navigate])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p style={{ color: 'var(--text-secondary)' }}>Loading...</p>
      </div>
    )
  }

  if (!user) {
    if (path === '/register') return <Register onNavigate={navigate} />
    return <Login onNavigate={navigate} />
  }

  const projectMatch = matchPath('/projects/:id', path)

  let content
  if (path === '/projects/new') {
    content = <CreateProject onNavigate={navigate} />
  } else if (projectMatch) {
    content = <ProjectDetail projectId={projectMatch.id} onNavigate={navigate} />
  } else {
    content = <ProjectList onNavigate={navigate} />
  }

  return (
    <AppLayout onNavigate={navigate}>
      {content}
    </AppLayout>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}
