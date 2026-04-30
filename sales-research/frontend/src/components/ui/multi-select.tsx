
import * as React from "react"
import * as ReactDOM from "react-dom"
import { X, Check, ChevronsUpDown, Search } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Label } from "@/components/ui/label"
import { cn } from "@/lib/utils"

export interface MultiSelectOption {
    label: string
    value: string
}

export interface MultiSelectProps {
    options: (string | MultiSelectOption)[]
    value: string | string[]
    onChange: (value: string[]) => void
    placeholder?: string
    label?: string
    allowCustom?: boolean
    disabled?: boolean
    hideSearch?: boolean
    className?: string
    usePortal?: boolean
}

export function MultiSelect({
    options,
    value,
    onChange,
    placeholder = "Select options...",
    label,
    allowCustom = false,
    disabled = false,
    hideSearch = false,
    className,
    usePortal = true,
}: MultiSelectProps) {
    const [open, setOpen] = React.useState(false)
    const [search, setSearch] = React.useState("")
    const [dropUp, setDropUp] = React.useState(false)
    const [dropdownStyle, setDropdownStyle] = React.useState<React.CSSProperties>({})
    const containerRef = React.useRef<HTMLDivElement>(null)
    const dropdownRef = React.useRef<HTMLDivElement>(null)
    const [mounted, setMounted] = React.useState(false)

    React.useEffect(() => { setMounted(true) }, [])

    const updatePosition = React.useCallback(() => {
        if (!containerRef.current) return
        const rect = containerRef.current.getBoundingClientRect()
        const spaceBelow = window.innerHeight - rect.bottom
        const du = spaceBelow < 320
        setDropUp(du)
        if (du) {
            setDropdownStyle(
                usePortal
                    ? { position: "fixed", bottom: window.innerHeight - rect.top + 4, left: rect.left, width: rect.width, zIndex: 9999 }
                    : { position: "absolute", bottom: "calc(100% + 4px)", left: 0, width: "100%", zIndex: 50 }
            )
        } else {
            setDropdownStyle(
                usePortal
                    ? { position: "fixed", top: rect.bottom + 4, left: rect.left, width: rect.width, zIndex: 9999 }
                    : { position: "absolute", top: "calc(100% + 4px)", left: 0, width: "100%", zIndex: 50 }
            )
        }
    }, [usePortal])

    // Close on outside click — must check both trigger and portal dropdown
    React.useEffect(() => {
        if (!open) return
        const handle = (e: MouseEvent) => {
            const target = e.target as Node
            if (
                containerRef.current?.contains(target) ||
                dropdownRef.current?.contains(target)
            ) return
            setOpen(false)
        }
        const id = setTimeout(() => document.addEventListener("mousedown", handle), 0)
        return () => {
            clearTimeout(id)
            document.removeEventListener("mousedown", handle)
        }
    }, [open])

    // Keep position in sync while open
    React.useEffect(() => {
        if (!open) return
        window.addEventListener("scroll", updatePosition, true)
        window.addEventListener("resize", updatePosition)
        return () => {
            window.removeEventListener("scroll", updatePosition, true)
            window.removeEventListener("resize", updatePosition)
        }
    }, [open, updatePosition])

    const handleOpen = () => {
        if (disabled) return
        if (!open) updatePosition()
        setOpen(v => !v)
    }

    const getOptionLabel = (o: string | MultiSelectOption) => typeof o === "string" ? o : o.label
    const getOptionValue = (o: string | MultiSelectOption) => typeof o === "string" ? o : o.value

    const selectedValues = React.useMemo(() => {
        if (!value) return []
        if (Array.isArray(value)) return value
        return value.split(",").map(s => s.trim()).filter(Boolean)
    }, [value])

    const uniqueOptions = React.useMemo(() => {
        const seen = new Set<string>()
        return options.filter(o => {
            const v = getOptionValue(o)
            if (seen.has(v)) return false
            seen.add(v)
            return true
        })
    }, [options])

    const filteredOptions = uniqueOptions.filter(o =>
        !selectedValues.includes(getOptionValue(o)) &&
        (hideSearch || getOptionLabel(o).toLowerCase().includes(search.toLowerCase()))
    )

    const optionsMap = React.useMemo(() => {
        const map = new Map<string, string>()
        uniqueOptions.forEach(o => map.set(getOptionValue(o), getOptionLabel(o)))
        return map
    }, [uniqueOptions])

    const handleSelect = (val: string) => {
        if (disabled || selectedValues.includes(val)) return
        onChange([...selectedValues, val])
        setSearch("")
    }

    const handleUnselect = (val: string) => {
        if (disabled) return
        onChange(selectedValues.filter(v => v !== val))
    }

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === "Enter" && allowCustom && search.trim()) {
            e.preventDefault()
            e.stopPropagation()
            handleSelect(search.trim())
        }
        if (e.key === "Backspace" && !search && selectedValues.length > 0) {
            handleUnselect(selectedValues[selectedValues.length - 1])
        }
        if (e.key === "Escape") setOpen(false)
    }

    const dropdown = open ? (
        <div
            ref={dropdownRef}
            style={dropdownStyle}
            className="rounded-md border bg-popover text-popover-foreground shadow-2xl"
        >
            {!hideSearch && (
                <div className="flex items-center border-b px-3 py-2 bg-muted/30">
                    <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
                    <input
                        autoFocus
                        className="flex h-8 w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
                        placeholder={allowCustom ? "Search or type to add..." : "Search..."}
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        onKeyDown={handleKeyDown}
                        onClick={e => e.stopPropagation()}
                    />
                </div>
            )}
            <div className="max-h-[260px] overflow-y-auto p-1">
                {allowCustom && !hideSearch && search.trim() &&
                 !uniqueOptions.some(o => getOptionLabel(o).toLowerCase() === search.toLowerCase()) && (
                    <div
                        className="flex w-full cursor-pointer items-center rounded-sm px-2 py-2 text-sm bg-primary/5 text-primary hover:bg-primary/10"
                        onMouseDown={e => { e.preventDefault(); handleSelect(search.trim()) }}
                    >
                        <X className="mr-2 h-4 w-4 rotate-45 shrink-0" />
                        Add "{search.trim()}"
                    </div>
                )}
                {filteredOptions.length === 0 && (!allowCustom || !search.trim()) ? (
                    <p className="py-6 text-center text-sm text-muted-foreground">No results found.</p>
                ) : (
                    filteredOptions.map(option => (
                        <div
                            key={getOptionValue(option)}
                            className="flex w-full cursor-pointer items-center rounded-sm px-2 py-2 text-sm hover:bg-primary/10 hover:text-primary"
                            onMouseDown={e => { e.preventDefault(); handleSelect(getOptionValue(option)) }}
                        >
                            {getOptionLabel(option)}
                        </div>
                    ))
                )}
                {selectedValues.length > 0 && (
                    <>
                        <div className="h-px bg-border my-1" />
                        <div className="px-2 py-1 text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Selected</div>
                        {selectedValues.map(val => (
                            <div key={`sel-${val}`} className="flex items-center rounded-sm px-2 py-2 text-sm bg-primary/5 text-primary/80">
                                <Check className="mr-2 h-4 w-4 shrink-0" />
                                {optionsMap.get(val) ?? val}
                            </div>
                        ))}
                    </>
                )}
            </div>
        </div>
    ) : null

    return (
        <div className={cn("space-y-2", className)}>
            {label && <Label>{label}</Label>}
            <div className="relative" ref={containerRef}>
                <div
                    className={cn(
                        "min-h-[42px] w-full rounded-md border border-input bg-background/50 px-3 py-2 text-sm ring-offset-background flex flex-wrap gap-1.5 items-center cursor-pointer transition-all",
                        disabled ? "opacity-50 cursor-not-allowed" : "hover:border-primary/50 focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2",
                        open && !disabled && "ring-2 ring-ring ring-offset-2 border-primary shadow-lg shadow-primary/10"
                    )}
                    onClick={handleOpen}
                >
                    {selectedValues.length > 0 ? (
                        selectedValues.map(val => (
                            <Badge
                                key={val}
                                variant="secondary"
                                className={cn("bg-primary/10 text-primary border-primary/20 transition-colors py-0.5 pl-2 pr-1 gap-1", !disabled && "hover:bg-primary/20")}
                            >
                                {optionsMap.get(val) ?? val}
                                {!disabled && (
                                    <button
                                        type="button"
                                        className="rounded-full outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 hover:bg-primary/30 p-0.5"
                                        onMouseDown={e => { e.preventDefault(); e.stopPropagation() }}
                                        onClick={e => { e.stopPropagation(); handleUnselect(val) }}
                                    >
                                        <X className="h-3 w-3" />
                                    </button>
                                )}
                            </Badge>
                        ))
                    ) : (
                        <span className="text-muted-foreground">{placeholder}</span>
                    )}
                    <div className="flex-1" />
                    <ChevronsUpDown className="h-4 w-4 shrink-0 opacity-50" />
                </div>
                {mounted && dropdown && (usePortal ? ReactDOM.createPortal(dropdown, document.body) : dropdown)}
            </div>
        </div>
    )
}
