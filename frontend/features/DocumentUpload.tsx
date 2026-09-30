'use client'

import React, { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { FileText, Loader2, UploadCloud, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useUploadDocument } from '@/hooks/useApi'

interface DocumentUploadProps {
  projectId: string
  onUploadComplete?: (document: any) => void
}

export function DocumentUploadComponent({ projectId, onUploadComplete }: DocumentUploadProps) {
  const [uploadedFiles, setUploadedFiles] = useState<any[]>([])
  const [uploading, setUploading] = useState(false)
  const uploadDocument = useUploadDocument()

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      setUploading(true)
      for (const file of acceptedFiles) {
        try {
          const result = await uploadDocument.mutateAsync({ projectId, file })
          setUploadedFiles((prev) => [...prev, result])
          onUploadComplete?.(result)
        } catch (error) {
          console.error('Upload failed:', error)
        }
      }
      setUploading(false)
    },
    [projectId, uploadDocument, onUploadComplete],
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.png', '.jpg', '.jpeg'],
      'application/msword': ['.doc', '.docx'],
    },
    maxSize: 50 * 1024 * 1024,
  })

  const statusConfig: Record<string, { variant: 'success' | 'warning' | 'danger' | 'default'; icon: any }> = {
    VERIFIED: { variant: 'success', icon: CheckCircle2 },
    WARNING: { variant: 'warning', icon: AlertTriangle },
    REJECTED: { variant: 'danger', icon: XCircle },
    PROCESSING: { variant: 'default', icon: Loader2 },
    UPLOADED: { variant: 'default', icon: FileText },
  }

  return (
    <div className="space-y-6">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition ${
          isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-blue-400'
        }`}
      >
        <input {...getInputProps()} />
        <div className="space-y-3">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-50">
            <UploadCloud className="w-8 h-8 text-blue-600" />
          </div>
          {isDragActive ? (
            <p className="text-blue-600 font-semibold">Drop files here...</p>
          ) : (
            <>
              <p className="text-gray-900 font-semibold">Drag & drop documents here</p>
              <p className="text-gray-600">or click to select files</p>
              <p className="text-sm text-gray-500">Supported: PDF, PNG, JPG, DOCX (Max 50MB)</p>
            </>
          )}
        </div>
      </div>

      {uploading && (
        <div className="flex items-center gap-2 text-sm text-blue-600 px-4 py-3 bg-blue-50 border border-blue-200 rounded-lg">
          <Loader2 className="w-4 h-4 animate-spin" />
          Uploading documents... This may take a moment.
        </div>
      )}

      {uploadedFiles.length > 0 && (
        <div className="space-y-3">
          <h4 className="font-semibold text-gray-900">Uploaded Documents</h4>
          <div className="space-y-2">
            {uploadedFiles.map((file, index) => {
              const config = statusConfig[file.status] || statusConfig.UPLOADED
              const StatusIcon = config.icon
              return (
                <div
                  key={index}
                  className="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-lg"
                >
                  <div className="flex items-center space-x-3 min-w-0">
                    <FileText className="w-5 h-5 text-gray-500 shrink-0" />
                    <div className="min-w-0">
                      <p className="font-medium text-gray-900 truncate">{file.file_name}</p>
                      <p className="text-sm text-gray-600">
                        {(file.file_size / 1024 / 1024).toFixed(2)} MB · {file.file_type}
                      </p>
                    </div>
                  </div>
                  <Badge variant={config.variant}>
                    <StatusIcon className="w-3 h-3 mr-1" />
                    {file.status}
                  </Badge>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {uploadedFiles.length === 0 && !uploading && (
        <div className="text-center py-6">
          <p className="text-sm text-gray-600">
            Uploaded documents with extracted fields will appear here. Validation results are shown when the document is processed.
          </p>
        </div>
      )}
    </div>
  )
}

export default DocumentUploadComponent