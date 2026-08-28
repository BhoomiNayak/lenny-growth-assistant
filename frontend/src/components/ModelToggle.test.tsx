import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ModelToggle } from './ModelToggle'
import type { ProviderConfig } from '../types'

const providers: ProviderConfig[] = [
  { provider: 'ollama', model: 'llama3.1:8b', available: true, reason: null },
  { provider: 'anthropic', model: 'claude-3-5-sonnet-20241022', available: false, reason: 'ANTHROPIC_API_KEY not set' },
]

describe('ModelToggle', () => {
  it('renders current provider and model', () => {
    render(<ModelToggle currentProvider="ollama" currentModel="llama3.1:8b" providers={providers} onSwitch={() => {}} />)
    expect(screen.getByText(/ollama/)).toBeInTheDocument()
    expect(screen.getByText(/llama3.1:8b/)).toBeInTheDocument()
  })

  it('opens dropdown on click', () => {
    render(<ModelToggle currentProvider="ollama" currentModel="llama3.1:8b" providers={providers} onSwitch={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: /switch model/i }))
    expect(screen.getByText('Select Model')).toBeInTheDocument()
  })

  it('calls onSwitch when an available provider is clicked', () => {
    const onSwitch = vi.fn()
    render(<ModelToggle currentProvider="ollama" currentModel="llama3.1:8b" providers={providers} onSwitch={onSwitch} />)
    fireEvent.click(screen.getByRole('button', { name: /switch model/i }))
    fireEvent.click(screen.getByText('ollama'))
    expect(onSwitch).toHaveBeenCalledWith('ollama', 'llama3.1:8b')
  })

  it('does not call onSwitch for unavailable providers', () => {
    const onSwitch = vi.fn()
    render(<ModelToggle currentProvider="ollama" currentModel="llama3.1:8b" providers={providers} onSwitch={onSwitch} />)
    fireEvent.click(screen.getByRole('button', { name: /switch model/i }))
    fireEvent.click(screen.getByText('anthropic'))
    expect(onSwitch).not.toHaveBeenCalled()
  })
})
