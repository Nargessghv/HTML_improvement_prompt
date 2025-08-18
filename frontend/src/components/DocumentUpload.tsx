'use client'

import React, { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { toast } from 'sonner'
import { useSupabaseAuth } from '@/hooks/useSupabaseAuthSimple'
import { 
  FileText, 
  FileType, 
  FileSpreadsheet, 
  Upload, 
  X, 
  Loader2, 
  CheckCircle,
  AlertCircle
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface DocumentFile {
  id?: string
  file: File
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'error'
  progress: number
  error?: string
  extractedText?: string
}

interface DocumentUploadProps {
  projectId?: string
  onDocumentsUploaded?: (documents: DocumentFile[]) => void
  maxFiles?: number
  maxSizeMB?: number
}

const ACCEPTED_FILE_TYPES = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'application/msword': ['.doc'],
  'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
  'application/vnd.ms-powerpoint': ['.ppt'],
  'text/plain': ['.txt'],
  'text/markdown': ['.md']
}

export function DocumentUpload({ 
  projectId, 
  onDocumentsUploaded,
  maxFiles = 5,
  maxSizeMB = 10
}: DocumentUploadProps) {
  const [documents, setDocuments] = useState<DocumentFile[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const { supabase } = useSupabaseAuth()

  const getFileIcon = (fileName: string) => {
    const ext = fileName.split('.').pop()?.toLowerCase()
    switch (ext) {
      case 'pdf':
        return <FileText className="w-5 h-5" />
      case 'doc':
      case 'docx':
        return <FileType className="w-5 h-5" />
      case 'ppt':
      case 'pptx':
        return <FileSpreadsheet className="w-5 h-5" />
      default:
        return <FileText className="w-5 h-5" />
    }
  }

  const uploadDocument = async (document: DocumentFile) => {
    if (!projectId) {
      // If no projectId yet, just mark as pending
      return document
    }

    try {
      // Update status to uploading
      setDocuments(prev => prev.map(d => 
        d.file === document.file 
          ? { ...d, status: 'uploading' as const, progress: 30 }
          : d
      ))

      const formData = new FormData()
      formData.append('file', document.file)

      // Get the Supabase session token
      const { data: { session } } = await supabase.auth.getSession()
      const token = session?.access_token

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/projects/${projectId}/documents`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      })

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`)
      }

      const result = await response.json()

      // Update document with success
      const updatedDoc: DocumentFile = {
        ...document,
        id: result.id,
        status: 'completed',
        progress: 100,
        extractedText: result.extracted_text
      }

      setDocuments(prev => prev.map(d => 
        d.file === document.file ? updatedDoc : d
      ))

      return updatedDoc

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed'
      
      // Update document with error
      setDocuments(prev => prev.map(d => 
        d.file === document.file 
          ? { ...d, status: 'error' as const, error: errorMessage }
          : d
      ))

      throw error
    }
  }

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    // Validate file count
    if (documents.length + acceptedFiles.length > maxFiles) {
      toast.error(`Maximum ${maxFiles} files allowed`)
      return
    }

    // Validate and add files
    const newDocuments: DocumentFile[] = []
    
    for (const file of acceptedFiles) {
      // Validate file size
      if (file.size > maxSizeMB * 1024 * 1024) {
        toast.error(`${file.name} exceeds ${maxSizeMB}MB limit`)
        continue
      }

      // Check if file already exists
      if (documents.some(d => d.file.name === file.name)) {
        toast.error(`${file.name} already added`)
        continue
      }

      newDocuments.push({
        file,
        status: 'pending',
        progress: 0
      })
    }

    if (newDocuments.length === 0) return

    // Add documents to state
    const updatedDocuments = [...documents, ...newDocuments]
    setDocuments(updatedDocuments)

    // Immediately notify parent of new documents (for use before project creation)
    if (onDocumentsUploaded) {
      onDocumentsUploaded(updatedDocuments)
    }

    // If we have a projectId, start uploading immediately
    if (projectId) {
      setIsUploading(true)
      
      try {
        const uploadPromises = newDocuments.map(doc => uploadDocument(doc))
        const uploadedDocs = await Promise.all(uploadPromises)
        
        toast.success(`${uploadedDocs.length} document(s) uploaded successfully`)
        
        if (onDocumentsUploaded) {
          onDocumentsUploaded(uploadedDocs)
        }
      } catch (error) {
        toast.error('Some documents failed to upload')
      } finally {
        setIsUploading(false)
      }
    }
  }, [documents, maxFiles, maxSizeMB, projectId, onDocumentsUploaded])

  const removeDocument = (index: number) => {
    const updatedDocuments = documents.filter((_, i) => i !== index)
    setDocuments(updatedDocuments)
    
    // Notify parent of the updated document list
    if (onDocumentsUploaded) {
      onDocumentsUploaded(updatedDocuments)
    }
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_FILE_TYPES,
    maxFiles: maxFiles - documents.length,
    disabled: isUploading || documents.length >= maxFiles
  })

  // Upload pending documents when projectId becomes available
  React.useEffect(() => {
    if (projectId && documents.some(d => d.status === 'pending')) {
      const uploadPending = async () => {
        setIsUploading(true)
        
        try {
          const pendingDocs = documents.filter(d => d.status === 'pending')
          const uploadPromises = pendingDocs.map(doc => uploadDocument(doc))
          await Promise.all(uploadPromises)
          
          toast.success('Documents uploaded successfully')
          
          if (onDocumentsUploaded) {
            onDocumentsUploaded(documents)
          }
        } catch (error) {
          toast.error('Failed to upload documents')
        } finally {
          setIsUploading(false)
        }
      }
      
      uploadPending()
    }
  }, [projectId])

  return (
    <div className="space-y-4">
      {/* Upload Area */}
      <div
        {...getRootProps()}
        className={cn(
          "border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors",
          isDragActive ? "border-primary bg-primary/5" : "border-gray-300 hover:border-gray-400",
          (isUploading || documents.length >= maxFiles) && "opacity-50 cursor-not-allowed"
        )}
      >
        <input {...getInputProps()} />
        
        <Upload className="w-10 h-10 mx-auto mb-3 text-gray-400" />
        
        {isDragActive ? (
          <p className="text-sm text-gray-600">Drop the files here...</p>
        ) : (
          <>
            <p className="text-sm text-gray-600 mb-1">
              Drag & drop documents here, or click to select
            </p>
            <p className="text-xs text-gray-400">
              Supports PDF, Word, PowerPoint, and text files (max {maxSizeMB}MB each)
            </p>
            <p className="text-xs text-gray-400 mt-1">
              {documents.length}/{maxFiles} files added
            </p>
          </>
        )}
      </div>

      {/* Document List */}
      {documents.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-700">Uploaded Documents</h4>
          
          {documents.map((doc, index) => (
            <Card key={index} className="p-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3 flex-1">
                  {getFileIcon(doc.file.name)}
                  
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {doc.file.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {(doc.file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                  
                  {/* Status Indicator */}
                  <div className="flex items-center space-x-2">
                    {doc.status === 'uploading' && (
                      <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                    )}
                    {doc.status === 'processing' && (
                      <Loader2 className="w-4 h-4 animate-spin text-yellow-500" />
                    )}
                    {doc.status === 'completed' && (
                      <CheckCircle className="w-4 h-4 text-green-500" />
                    )}
                    {doc.status === 'error' && (
                      <AlertCircle className="w-4 h-4 text-red-500" />
                    )}
                    
                    <span className="text-xs text-gray-500 capitalize">
                      {doc.status}
                    </span>
                  </div>
                </div>
                
                {/* Remove Button */}
                {!isUploading && doc.status !== 'uploading' && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeDocument(index)}
                    className="ml-2"
                  >
                    <X className="w-4 h-4" />
                  </Button>
                )}
              </div>
              
              {/* Progress Bar */}
              {(doc.status === 'uploading' || doc.status === 'processing') && (
                <Progress value={doc.progress} className="mt-2 h-1" />
              )}
              
              {/* Error Message */}
              {doc.error && (
                <p className="text-xs text-red-500 mt-2">{doc.error}</p>
              )}
            </Card>
          ))}
        </div>
      )}
      
      {/* Info Text */}
      {documents.length > 0 && (
        <p className="text-xs text-gray-500 text-center">
          These documents will be used as context for generating your presentation content
        </p>
      )}
    </div>
  )
}