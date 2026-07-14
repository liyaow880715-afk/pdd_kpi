import { useCallback, useState } from "react"
import { Upload, File } from "lucide-react"
import { cn } from "@/lib/utils"

interface FileDropzoneProps {
  accept?: string
  label: string
  description?: string
  value?: File | null
  onChange: (file: File | null) => void
}

export function FileDropzone({ accept, label, description, value, onChange }: FileDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)
      const droppedFile = e.dataTransfer.files?.[0]
      if (droppedFile) {
        onChange(droppedFile)
      }
    },
    [onChange]
  )

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selectedFile = e.target.files?.[0]
      if (selectedFile) {
        onChange(selectedFile)
      }
    },
    [onChange]
  )

  return (
    <label
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={cn(
        "flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-6 transition-colors cursor-pointer hover:bg-muted/50",
        isDragging ? "border-primary bg-primary/5" : "border-border"
      )}
    >
      <input
        type="file"
        accept={accept}
        onChange={handleInputChange}
        className="sr-only"
      />
      {value ? (
        <>
          <File className="h-8 w-8 text-primary" />
          <span className="text-sm font-medium text-foreground">{value.name}</span>
          <span className="text-xs text-muted-foreground">点击或拖拽替换文件</span>
        </>
      ) : (
        <>
          <Upload className="h-8 w-8 text-muted-foreground" />
          <span className="text-sm font-medium">{label}</span>
          {description && <span className="text-xs text-muted-foreground">{description}</span>}
        </>
      )}
    </label>
  )
}
