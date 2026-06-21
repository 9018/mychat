import { useState } from 'react'
import { TweaksProvider, useTweaks } from '@/contexts/TweaksContext'
import { ConfigProvider } from '@/contexts/ConfigContext'
import { KeyProvider, useKey } from '@/contexts/KeyContext'
import { HistoryProvider } from '@/contexts/HistoryContext'
import { NavRail } from '@/components/Layout/NavRail'
import { MobileNav } from '@/components/Layout/MobileNav'
import { TopBar } from '@/components/Layout/TopBar'
import { TweaksPanel } from '@/components/Layout/TweaksPanel'
import { ToastContainer } from '@/components/common/Toast'
import { VideoPage } from '@/pages/VideoPage'
import { ImagePage } from '@/pages/ImagePage'
import { ChatPage } from '@/pages/ChatPage'
import { AdminPage } from '@/pages/AdminPage'
import { MaterialPage } from '@/pages/MaterialPage'
import type { TabType, VideoMode, ImgMode } from '@/api/types'

function AppContent() {
  const [activeTab, setActiveTab] = useState<TabType>('image')
  const [videoMode, setVideoMode] = useState<VideoMode>('text')
  const [imgMode, setImgMode] = useState<ImgMode>('txt2img')
  const [showTweaks, setShowTweaks] = useState(false)
  const { isReady } = useKey()

  const toggleTweaks = () => setShowTweaks(!showTweaks)

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <NavRail activeTab={activeTab} onTabChange={setActiveTab}
        onTweaksToggle={toggleTweaks} isKeyReady={isReady} />

      <div className="app-content" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <TopBar activeTab={activeTab} videoMode={videoMode} imgMode={imgMode}
          onVideoModeChange={setVideoMode} onImgModeChange={setImgMode}
          currentSection={activeTab} />

        <div style={{ flex: 1, overflow: 'auto' }}>
          {activeTab === 'video' && <VideoPage videoMode={videoMode} onVideoModeChange={setVideoMode} />}
          {activeTab === 'image' && <ImagePage imgMode={imgMode} onImgModeChange={setImgMode} />}
          {activeTab === 'chat' && <ChatPage />}
          {activeTab === 'admin' && <AdminPage />}
          {activeTab === 'material' && <MaterialPage />}
        </div>
      </div>

      {/* Mobile bottom nav */}
      <MobileNav activeTab={activeTab} onTabChange={setActiveTab}
        isKeyReady={isReady} onTweaksToggle={toggleTweaks} />

      {showTweaks && <div style={{ position: 'fixed', right: 16, bottom: 80, zIndex: 2147483646 }}>
        <TweaksPanel />
      </div>}

      <ToastContainer />
    </div>
  )
}

export default function App() {
  return (
    <TweaksProvider>
      <ConfigProvider>
        <KeyProvider>
          <HistoryProvider>
            <AppContent />
          </HistoryProvider>
        </KeyProvider>
      </ConfigProvider>
    </TweaksProvider>
  )
}
