import { File as FileIcon, FolderOpen, Upload, X } from "lucide-react"
import { useRef, useState } from "react"
import { Llm4AdTasksService } from "@/client"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface DataPreparationStepProps {
  taskId: string
  onNext: () => void
}

export default function DataPreparationStep({
  taskId,
  onNext,
}: DataPreparationStepProps) {
  const [files, setFiles] = useState<File[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  // set webkitdirectory via ref since it's not in React's type definitions
  const setInputRef = (el: HTMLInputElement | null) => {
    if (el) el.setAttribute("webkitdirectory", "")
    inputRef.current = el
  }

  const addFiles = (fileList: FileList) => {
    const newFiles = Array.from(fileList)
    if (newFiles.length === 0) return
    setFiles((prev) => {
      const existingPaths = new Set(
        prev.map((f) => f.webkitRelativePath || f.name),
      )
      const unique = newFiles.filter(
        (f) => !existingPaths.has(f.webkitRelativePath || f.name),
      )
      return [...prev, ...unique]
    })
  }

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index))
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files.length > 0) {
      addFiles(e.dataTransfer.files)
    }
  }

  const handleUpload = async () => {
    if (files.length === 0) return
    setUploading(true)
    try {
      await Llm4AdTasksService.uploadTaskData({
        taskId,
        formData: { files },
      })
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold">数据准备</h3>
        <p className="text-sm text-muted-foreground mt-1">
          选择目录上传数据文件
        </p>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault()
          setIsDragging(true)
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed p-12 transition-colors",
          isDragging
            ? "border-primary bg-primary/5"
            : "border-muted-foreground/25 hover:border-muted-foreground/50",
        )}
      >
        <FolderOpen className="size-10 text-muted-foreground" />
        <div className="text-center">
          <p className="text-sm font-medium">点击选择目录或拖拽文件上传</p>
          <p className="text-xs text-muted-foreground mt-1">
            选择目录后将上传目录下所有文件
          </p>
        </div>
        <input
          ref={setInputRef}
          type="file"
          className="hidden"
          multiple
          onChange={(e) => {
            if (e.target.files) addFiles(e.target.files)
            e.target.value = ""
          }}
        />
      </div>

      {files.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">
            已选择 {files.length} 个文件
          </p>
          <div className="max-h-60 overflow-y-auto space-y-1">
            {files.map((file, index) => (
              <div
                key={file.webkitRelativePath || file.name}
                className="flex items-center gap-3 rounded-lg border bg-card p-2"
              >
                <FileIcon className="size-4 shrink-0 text-muted-foreground" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm truncate">
                    {file.webkitRelativePath || file.name}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {(file.size / 1024).toFixed(1)} KB
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={(e) => {
                    e.stopPropagation()
                    removeFile(index)
                  }}
                >
                  <X className="size-4" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {files.length > 0 && !uploading && (
        <Button variant="outline" size="sm" onClick={handleUpload}>
          <Upload className="size-4 mr-1" />
          上传 {files.length} 个文件
        </Button>
      )}

      <div className="flex justify-end pt-4 border-t">
        <Button onClick={onNext}>下一步</Button>
      </div>
    </div>
  )
}
