import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface SlideDraft {
  id: string
  project_id: string
  slide_number: number
  title?: string
  content?: any
  html_content?: string
  refined_html?: string
  status: 'pending' | 'generating' | 'generated' | 'editing' | 'approved' | 'failed'
  placeholder_info?: any
  layout_type?: string
  created_at: string
  updated_at: string
}

export interface EditRequest {
  id: string
  slide_draft_id: string
  request_type: 'content' | 'html' | 'layout' | 'style' | 'regenerate'
  request_details: any
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'
  result?: any
  error_message?: string
  created_at: string
  processed_at?: string
  completed_at?: string
}

export interface SlideComment {
  id: string
  slide_draft_id: string
  user_id: string
  comment_text: string
  comment_type: 'feedback' | 'edit_request' | 'approval' | 'rejection'
  resolved: boolean
  created_at: string
}

interface InteractiveSlideStore {
  // State
  slides: Map<string, SlideDraft>
  editRequests: Map<string, EditRequest>
  comments: Map<string, SlideComment[]>
  activeSlideId: string | null
  presentationOutline: any | null
  chatSessionId: string | null
  isGenerating: boolean

  // Actions - Slides
  setSlides: (slides: SlideDraft[]) => void
  updateSlide: (slideId: string, updates: Partial<SlideDraft>) => void
  addSlide: (slide: SlideDraft) => void
  removeSlide: (slideId: string) => void
  setActiveSlide: (slideId: string | null) => void

  // Actions - Edit Requests
  addEditRequest: (request: EditRequest) => void
  updateEditRequest: (requestId: string, updates: Partial<EditRequest>) => void
  getSlideEditRequests: (slideId: string) => EditRequest[]

  // Actions - Comments
  addComment: (comment: SlideComment) => void
  updateComment: (commentId: string, updates: Partial<SlideComment>) => void
  getSlideComments: (slideId: string) => SlideComment[]

  // Actions - Presentation
  setPresentationOutline: (outline: any) => void
  setChatSessionId: (sessionId: string | null) => void
  setIsGenerating: (isGenerating: boolean) => void

  // Computed
  getSlidesArray: () => SlideDraft[]
  getSlideByNumber: (slideNumber: number) => SlideDraft | undefined
  getApprovedSlides: () => SlideDraft[]
  getPendingEditRequests: () => EditRequest[]

  // Reset
  reset: () => void
}

export const useInteractiveSlideStore = create<InteractiveSlideStore>()(
  persist(
    (set, get) => ({
      // Initial state
      slides: new Map(),
      editRequests: new Map(),
      comments: new Map(),
      activeSlideId: null,
      presentationOutline: null,
      chatSessionId: null,
      isGenerating: false,

      // Slide actions
      setSlides: (slides) => {
        const slidesMap = new Map()
        slides.forEach(slide => slidesMap.set(slide.id, slide))
        set({ slides: slidesMap })
      },

      updateSlide: (slideId, updates) => {
        set((state) => {
          const slides = new Map(state.slides)
          const existing = slides.get(slideId)
          if (existing) {
            slides.set(slideId, { ...existing, ...updates, updated_at: new Date().toISOString() })
          }
          return { slides }
        })
      },

      addSlide: (slide) => {
        set((state) => {
          const slides = new Map(state.slides)
          slides.set(slide.id, slide)
          return { slides }
        })
      },

      removeSlide: (slideId) => {
        set((state) => {
          const slides = new Map(state.slides)
          slides.delete(slideId)
          
          // Also remove associated edit requests and comments
          const editRequests = new Map(state.editRequests)
          const comments = new Map(state.comments)
          
          // Remove edit requests for this slide
          Array.from(editRequests.values()).forEach(request => {
            if (request.slide_draft_id === slideId) {
              editRequests.delete(request.id)
            }
          })
          
          // Remove comments for this slide
          comments.delete(slideId)
          
          return { slides, editRequests, comments }
        })
      },

      setActiveSlide: (slideId) => set({ activeSlideId: slideId }),

      // Edit request actions
      addEditRequest: (request) => {
        set((state) => {
          const editRequests = new Map(state.editRequests)
          editRequests.set(request.id, request)
          return { editRequests }
        })
      },

      updateEditRequest: (requestId, updates) => {
        set((state) => {
          const editRequests = new Map(state.editRequests)
          const existing = editRequests.get(requestId)
          if (existing) {
            editRequests.set(requestId, { ...existing, ...updates })
          }
          return { editRequests }
        })
      },

      getSlideEditRequests: (slideId) => {
        const { editRequests } = get()
        return Array.from(editRequests.values()).filter(
          request => request.slide_draft_id === slideId
        )
      },

      // Comment actions
      addComment: (comment) => {
        set((state) => {
          const comments = new Map(state.comments)
          const slideComments = comments.get(comment.slide_draft_id) || []
          comments.set(comment.slide_draft_id, [...slideComments, comment])
          return { comments }
        })
      },

      updateComment: (commentId, updates) => {
        set((state) => {
          const comments = new Map(state.comments)
          
          // Find and update the comment
          for (const [slideId, slideComments] of comments.entries()) {
            const index = slideComments.findIndex(c => c.id === commentId)
            if (index !== -1) {
              const updatedComments = [...slideComments]
              updatedComments[index] = { ...updatedComments[index], ...updates }
              comments.set(slideId, updatedComments)
              break
            }
          }
          
          return { comments }
        })
      },

      getSlideComments: (slideId) => {
        const { comments } = get()
        return comments.get(slideId) || []
      },

      // Presentation actions
      setPresentationOutline: (outline) => set({ presentationOutline: outline }),
      setChatSessionId: (sessionId) => set({ chatSessionId: sessionId }),
      setIsGenerating: (isGenerating) => set({ isGenerating }),

      // Computed getters
      getSlidesArray: () => {
        const { slides } = get()
        return Array.from(slides.values()).sort((a, b) => a.slide_number - b.slide_number)
      },

      getSlideByNumber: (slideNumber) => {
        const { slides } = get()
        return Array.from(slides.values()).find(slide => slide.slide_number === slideNumber)
      },

      getApprovedSlides: () => {
        const { slides } = get()
        return Array.from(slides.values())
          .filter(slide => slide.status === 'approved')
          .sort((a, b) => a.slide_number - b.slide_number)
      },

      getPendingEditRequests: () => {
        const { editRequests } = get()
        return Array.from(editRequests.values())
          .filter(request => request.status === 'pending' || request.status === 'processing')
          .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      },

      // Reset
      reset: () => set({
        slides: new Map(),
        editRequests: new Map(),
        comments: new Map(),
        activeSlideId: null,
        presentationOutline: null,
        chatSessionId: null,
        isGenerating: false
      })
    }),
    {
      name: 'interactive-slide-store',
      // Custom serialization for Maps
      serialize: (state) => {
        return JSON.stringify({
          ...state,
          slides: Array.from(state.slides.entries()),
          editRequests: Array.from(state.editRequests.entries()),
          comments: Array.from(state.comments.entries())
        })
      },
      deserialize: (str) => {
        const parsed = JSON.parse(str)
        return {
          ...parsed,
          slides: new Map(parsed.slides || []),
          editRequests: new Map(parsed.editRequests || []),
          comments: new Map(parsed.comments || [])
        }
      }
    }
  )
)