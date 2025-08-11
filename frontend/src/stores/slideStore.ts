// Slide state management with Zustand
import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'
import { Slide, ChatMessage, Conversation } from '@/types'

interface EditorSelection {
  elementId: string | null
  element: HTMLElement | null
  bounds: DOMRect | null
}

interface EditorHistory {
  past: string[]
  present: string
  future: string[]
}

interface SlideState {
  // Slide data
  slides: Slide[]
  currentSlide: Slide | null
  
  // Editor state
  isEditing: boolean
  selectedElements: EditorSelection[]
  htmlHistory: Record<string, EditorHistory>
  
  // Chat conversation
  conversations: Record<string, Conversation>
  activeConversation: string | null
  
  // Loading and error states
  isLoading: boolean
  error: string | null
  
  // View state
  viewMode: 'thumbnail' | 'list' | 'grid'
  zoom: number
  viewport: { width: number; height: number }
}

interface SlideActions {
  // Slide CRUD
  setSlides: (slides: Slide[]) => void
  addSlide: (slide: Slide) => void
  updateSlide: (id: string, updates: Partial<Slide>) => void
  removeSlide: (id: string) => void
  reorderSlides: (oldIndex: number, newIndex: number) => void
  duplicateSlide: (id: string) => void
  
  // Current slide
  setCurrentSlide: (slide: Slide | null) => void
  selectSlideById: (id: string) => void
  
  // Editor actions
  startEditing: () => void
  stopEditing: () => void
  selectElement: (selection: EditorSelection) => void
  clearSelection: () => void
  updateSelectedElement: (updates: Record<string, unknown>) => void
  
  // HTML editing with undo/redo
  updateSlideHtml: (slideId: string, html: string) => void
  undoHtmlChange: (slideId: string) => void
  redoHtmlChange: (slideId: string) => void
  canUndo: (slideId: string) => boolean
  canRedo: (slideId: string) => boolean
  
  // Chat conversation
  createConversation: (slideId: string) => void
  addMessage: (conversationId: string, message: Omit<ChatMessage, 'id' | 'timestamp'>) => void
  setActiveConversation: (conversationId: string | null) => void
  
  // View controls
  setViewMode: (mode: 'thumbnail' | 'list' | 'grid') => void
  setZoom: (zoom: number) => void
  setViewport: (width: number, height: number) => void
  
  // Utility
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  resetSlideEditor: () => void
}

export type SlideStore = SlideState & SlideActions

const defaultViewport = { width: 1577, height: 603 } // Default PowerPoint slide dimensions for preview (actual dimensions are now dynamic)

export const useSlideStore = create<SlideStore>()(
  subscribeWithSelector((set, get) => ({
    // Initial state
    slides: [],
    currentSlide: null,
    isEditing: false,
    selectedElements: [],
    htmlHistory: {},
    conversations: {},
    activeConversation: null,
    isLoading: false,
    error: null,
    viewMode: 'thumbnail',
    zoom: 1,
    viewport: defaultViewport,

    // Slide CRUD actions
    setSlides: (slides) =>
      set(() => ({
        slides: slides.sort((a, b) => a.slide_number - b.slide_number)
      })),

    addSlide: (slide) =>
      set((state) => ({
        slides: [...state.slides, slide].sort((a, b) => a.slide_number - b.slide_number)
      })),

    updateSlide: (id, updates) =>
      set((state) => ({
        slides: state.slides.map(slide =>
          slide.id === id ? { ...slide, ...updates } : slide
        ),
        currentSlide: state.currentSlide?.id === id
          ? { ...state.currentSlide, ...updates }
          : state.currentSlide
      })),

    removeSlide: (id) =>
      set((state) => ({
        slides: state.slides.filter(slide => slide.id !== id),
        currentSlide: state.currentSlide?.id === id ? null : state.currentSlide
      })),

    reorderSlides: (oldIndex, newIndex) =>
      set((state) => {
        const newSlides = [...state.slides]
        const [moved] = newSlides.splice(oldIndex, 1)
        newSlides.splice(newIndex, 0, moved)
        
        // Update slide numbers
        const updatedSlides = newSlides.map((slide, index) => ({
          ...slide,
          slide_number: index + 1
        }))
        
        return { slides: updatedSlides }
      }),

    duplicateSlide: (id) =>
      set((state) => {
        const slide = state.slides.find(s => s.id === id)
        if (!slide) return state

        const newSlide: Slide = {
          ...slide,
          id: `duplicate-${id}-${Date.now()}`,
          slide_number: slide.slide_number + 1,
          title: `${slide.title} (Copy)`,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        }

        // Increment slide numbers for slides after the duplicated one
        const updatedSlides = state.slides.map(s =>
          s.slide_number > slide.slide_number
            ? { ...s, slide_number: s.slide_number + 1 }
            : s
        )

        return {
          slides: [...updatedSlides, newSlide].sort((a, b) => a.slide_number - b.slide_number)
        }
      }),

    // Current slide actions
    setCurrentSlide: (slide) =>
      set(() => ({
        currentSlide: slide,
        selectedElements: [], // Clear selection when changing slides
        isEditing: false
      })),

    selectSlideById: (id) =>
      set((state) => {
        const slide = state.slides.find(s => s.id === id)
        return slide ? { currentSlide: slide, selectedElements: [], isEditing: false } : state
      }),

    // Editor actions
    startEditing: () =>
      set(() => ({
        isEditing: true
      })),

    stopEditing: () =>
      set(() => ({
        isEditing: false,
        selectedElements: []
      })),

    selectElement: (selection) =>
      set(() => ({
        selectedElements: [selection]
      })),

    clearSelection: () =>
      set(() => ({
        selectedElements: []
      })),

    updateSelectedElement: (_updates) =>
      set((state) => {
        if (!state.currentSlide || state.selectedElements.length === 0) return state

        // This would typically update the HTML content
        // Implementation depends on how HTML manipulation is handled
        return state
      }),

    // HTML editing with history
    updateSlideHtml: (slideId, html) =>
      set((state) => {
        const slide = state.slides.find(s => s.id === slideId)
        if (!slide) return state

        const currentHistory = state.htmlHistory[slideId] || {
          past: [],
          present: slide.refined_html || slide.html_content || '',
          future: []
        }

        const newHistory = {
          past: [...currentHistory.past, currentHistory.present],
          present: html,
          future: [] // Clear redo history on new change
        }

        return {
          slides: state.slides.map(s =>
            s.id === slideId
              ? { ...s, refined_html: html, updated_at: new Date().toISOString() }
              : s
          ),
          currentSlide: state.currentSlide?.id === slideId
            ? { ...state.currentSlide, refined_html: html, updated_at: new Date().toISOString() }
            : state.currentSlide,
          htmlHistory: {
            ...state.htmlHistory,
            [slideId]: newHistory
          }
        }
      }),

    undoHtmlChange: (slideId) =>
      set((state) => {
        const history = state.htmlHistory[slideId]
        if (!history || history.past.length === 0) return state

        const previous = history.past[history.past.length - 1]
        const newHistory = {
          past: history.past.slice(0, -1),
          present: previous,
          future: [history.present, ...history.future]
        }

        return {
          slides: state.slides.map(s =>
            s.id === slideId
              ? { ...s, refined_html: previous, updated_at: new Date().toISOString() }
              : s
          ),
          currentSlide: state.currentSlide?.id === slideId
            ? { ...state.currentSlide, refined_html: previous, updated_at: new Date().toISOString() }
            : state.currentSlide,
          htmlHistory: {
            ...state.htmlHistory,
            [slideId]: newHistory
          }
        }
      }),

    redoHtmlChange: (slideId) =>
      set((state) => {
        const history = state.htmlHistory[slideId]
        if (!history || history.future.length === 0) return state

        const next = history.future[0]
        const newHistory = {
          past: [...history.past, history.present],
          present: next,
          future: history.future.slice(1)
        }

        return {
          slides: state.slides.map(s =>
            s.id === slideId
              ? { ...s, refined_html: next, updated_at: new Date().toISOString() }
              : s
          ),
          currentSlide: state.currentSlide?.id === slideId
            ? { ...state.currentSlide, refined_html: next, updated_at: new Date().toISOString() }
            : state.currentSlide,
          htmlHistory: {
            ...state.htmlHistory,
            [slideId]: newHistory
          }
        }
      }),

    canUndo: (slideId) => {
      const state = get()
      const history = state.htmlHistory[slideId]
      return !!(history && history.past.length > 0)
    },

    canRedo: (slideId) => {
      const state = get()
      const history = state.htmlHistory[slideId]
      return !!(history && history.future.length > 0)
    },

    // Chat conversation actions
    createConversation: (slideId) =>
      set((state) => {
        const conversationId = `conv-${slideId}-${Date.now()}`
        const conversation: Conversation = {
          id: conversationId,
          project_id: state.currentSlide?.project_id || '',
          slide_id: slideId,
          messages: [],
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        }

        return {
          conversations: {
            ...state.conversations,
            [conversationId]: conversation
          },
          activeConversation: conversationId
        }
      }),

    addMessage: (conversationId, message) =>
      set((state) => {
        const conversation = state.conversations[conversationId]
        if (!conversation) return state

        const newMessage: ChatMessage = {
          id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          timestamp: new Date().toISOString(),
          ...message
        }

        return {
          conversations: {
            ...state.conversations,
            [conversationId]: {
              ...conversation,
              messages: [...conversation.messages, newMessage],
              updated_at: new Date().toISOString()
            }
          }
        }
      }),

    setActiveConversation: (conversationId) =>
      set(() => ({
        activeConversation: conversationId
      })),

    // View controls
    setViewMode: (mode) =>
      set(() => ({
        viewMode: mode
      })),

    setZoom: (zoom) =>
      set(() => ({
        zoom: Math.max(0.1, Math.min(5, zoom))
      })),

    setViewport: (width, height) =>
      set(() => ({
        viewport: { width, height }
      })),

    // Utility actions
    setLoading: (loading) =>
      set(() => ({
        isLoading: loading
      })),

    setError: (error) =>
      set(() => ({
        error
      })),

    resetSlideEditor: () =>
      set(() => ({
        currentSlide: null,
        isEditing: false,
        selectedElements: [],
        activeConversation: null,
        error: null
      }))
  }))
)

// Selectors for better performance
export const useSlides = () => useSlideStore((state) => ({
  slides: state.slides,
  isLoading: state.isLoading,
  error: state.error
}))

export const useCurrentSlide = () => useSlideStore((state) => state.currentSlide)

export const useSlideEditor = () => useSlideStore((state) => ({
  isEditing: state.isEditing,
  selectedElements: state.selectedElements,
  startEditing: state.startEditing,
  stopEditing: state.stopEditing,
  selectElement: state.selectElement,
  clearSelection: state.clearSelection
}))

export const useSlideActions = () => useSlideStore((state) => ({
  setSlides: state.setSlides,
  addSlide: state.addSlide,
  updateSlide: state.updateSlide,
  removeSlide: state.removeSlide,
  reorderSlides: state.reorderSlides,
  duplicateSlide: state.duplicateSlide,
  setCurrentSlide: state.setCurrentSlide,
  selectSlideById: state.selectSlideById
}))

export const useSlideHistory = (slideId: string) => useSlideStore((state) => ({
  canUndo: state.canUndo(slideId),
  canRedo: state.canRedo(slideId),
  undo: () => state.undoHtmlChange(slideId),
  redo: () => state.redoHtmlChange(slideId),
  updateHtml: (html: string) => state.updateSlideHtml(slideId, html)
}))

export const useSlideConversation = (slideId: string) => useSlideStore((state) => {
  const conversationId = Object.keys(state.conversations).find(
    id => state.conversations[id].slide_id === slideId
  )
  
  return {
    conversation: conversationId ? state.conversations[conversationId] : null,
    isActive: state.activeConversation === conversationId,
    createConversation: () => state.createConversation(slideId),
    addMessage: conversationId ? (message: Omit<ChatMessage, 'id' | 'timestamp'>) => 
      state.addMessage(conversationId, message) : undefined,
    setActive: conversationId ? () => state.setActiveConversation(conversationId) : undefined
  }
})