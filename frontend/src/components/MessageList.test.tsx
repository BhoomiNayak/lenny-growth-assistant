import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MessageList } from './MessageList'
import type { Message } from '../types'

const messages: Message[] = [
  {
    id: '1',
    session_id: 's1',
    role: 'user',
    content: 'What is PMF?',
    created_at: '2026-08-27T10:00:00Z',
  },
  {
    id: '2',
    session_id: 's1',
    role: 'assistant',
    content: 'Product-market fit is...',
    sources: [{ title: 'Lenny Podcast', guest: 'Guest' }],
    created_at: '2026-08-27T10:00:05Z',
  },
]

describe('MessageList', () => {
  it('renders user and assistant messages', () => {
    render(<MessageList messages={messages} isStreaming={false} streamingContent="" />)
    expect(screen.getByText('What is PMF?')).toBeInTheDocument()
    expect(screen.getByText(/Product-market fit is/)).toBeInTheDocument()
  })

  it('shows typing indicator while streaming', () => {
    render(<MessageList messages={[]} isStreaming={true} streamingContent="" />)
    expect(screen.getByLabelText('Assistant is typing')).toBeInTheDocument()
  })

  it('renders streaming content when available', () => {
    render(<MessageList messages={[]} isStreaming={true} streamingContent="Partial answer..." />)
    expect(screen.getByText('Partial answer...')).toBeInTheDocument()
  })
})
