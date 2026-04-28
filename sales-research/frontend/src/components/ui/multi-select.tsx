
import * as React from "react"
import { X, Check, ChevronsUpDown, Search } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
    FormItem,
    FormLabel,
    FormControl,
    FormMessage,
} from "@/components/ui/form"
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
}: MultiSelectProps) {
    const [open, setOpen] = React.useState(false)
    const [search, setSearch] = React.useState("")

    const getOptionLabel = (option: string | MultiSelectOption) => 
        typeof option === "string" ? option : option.label

    const getOptionValue = (option: string | MultiSelectOption) => 
        typeof option === "string" ? option : option.value

    const uniqueOptions = React.useMemo(() => {
        const seen = new Set()
        return options.filter(option => {
            const val = getOptionValue(option)
            if (seen.has(val)) return false
            seen.add(val)
            return true
        })
    }, [options])

    const selectedValues = React.useMemo(() => {
        if (!value) return []
        if (Array.isArray(value)) return value
        return value.split(",").map(s => s.trim()).filter(Boolean)
    }, [value])

    const filteredOptions = uniqueOptions.filter(option => {
        const optionLabel = getOptionLabel(option)
        const optionValue = getOptionValue(option)
        const matchesSearch = hideSearch || optionLabel.toLowerCase().includes(search.toLowerCase())
        const isNotSelected = !selectedValues.includes(optionValue)
        return matchesSearch && isNotSelected
    })

    const handleUnselect = (val: string) => {
        if (disabled) return
        onChange(selectedValues.filter((v) => v !== val))
    }

    const handleSelect = (val: string) => {
        if (disabled) return
        if (!selectedValues.includes(val)) {
            onChange([...selectedValues, val])
        }
        setSearch("")
    }

    const optionsMap = React.useMemo(() => {
        const map = new Map<string, string>()
        options.forEach(option => {
            map.set(getOptionValue(option), getOptionLabel(option))
        })
        return map
    }, [options, getOptionValue, getOptionLabel])

    const getItemLabel = (val: string) => optionsMap.get(val) || val

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (disabled) return
        if (e.key === "Enter" && allowCustom && search.trim()) {
            e.preventDefault()
            e.stopPropagation()
            handleSelect(search.trim())
        }
        if (e.key === "Backspace" && !search && selectedValues.length > 0) {
            handleUnselect(selectedValues[selectedValues.length - 1])
        }
    }

    return (
        <div className={cn("space-y-2", className)}>
            {label && <FormLabel>{label}</FormLabel>}
            <div className="relative">
                <div
                    className={cn(
                        "min-h-[42px] w-full rounded-md border border-input bg-background/50 px-3 py-2 text-sm ring-offset-background flex flex-wrap gap-1.5 items-center cursor-pointer transition-all",
                        disabled ? "opacity-50 cursor-not-allowed" : "hover:border-primary/50 focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2",
                        open && !disabled && "ring-2 ring-ring ring-offset-2 border-primary shadow-lg shadow-primary/10"
                    )}
                    onClick={() => !disabled && setOpen(!open)}
                >
                    {selectedValues.length > 0 ? (
                        selectedValues.map((val) => (
                            <Badge
                                key={val}
                                variant="secondary"
                                className={cn(
                                    "bg-primary/10 text-primary border-primary/20 transition-colors py-0.5 pl-2 pr-1 gap-1",
                                    !disabled && "hover:bg-primary/20"
                                )}
                            >
                                {getItemLabel(val)}
                                {!disabled && (
                                    <button
                                        type="button"
                                        className="rounded-full outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 hover:bg-primary/30 p-0.5"
                                        onKeyDown={(e) => {
                                            if (e.key === "Enter") {
                                                handleUnselect(val)
                                            }
                                        }}
                                        onMouseDown={(e) => {
                                            e.preventDefault()
                                            e.stopPropagation()
                                        }}
                                        onClick={() => handleUnselect(val)}
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

                {open && (
                    <>
                        <div
                            className="fixed inset-0 z-40"
                            onClick={() => setOpen(false)}
                        />
                        <div className="absolute z-50 mt-2 w-full rounded-md border bg-popover text-popover-foreground shadow-2xl animate-in fade-in zoom-in-95 duration-200 overflow-hidden backdrop-blur-md">
                            {!hideSearch && (
                                <div className="flex items-center border-b px-3 py-2 bg-muted/30">
                                    <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
                                    <input
                                        className="flex h-8 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
                                        placeholder={allowCustom ? "Search or type new..." : "Search..."}
                                        value={search}
                                        onChange={(e) => setSearch(e.target.value)}
                                        onKeyDown={handleKeyDown}
                                        autoFocus
                                        onClick={(e) => e.stopPropagation()}
                                    />
                                </div>
                            )}
                            <div className="max-h-[300px] overflow-y-auto p-1 custom-scrollbar">
                                {allowCustom && !hideSearch && search.trim() && !options.some(o => getOptionLabel(o).toLowerCase() === search.toLowerCase()) && (
                                    <div
                                        className="relative flex w-full cursor-pointer select-none items-center rounded-sm px-2 py-2 text-sm outline-none bg-primary/5 text-primary hover:bg-primary/10 transition-colors"
                                        onClick={(e) => {
                                            e.stopPropagation()
                                            handleSelect(search.trim())
                                        }}
                                    >
                                        <X className="mr-2 h-4 w-4 rotate-45" />
                                        Add "{search.trim()}"
                                        <span className="ml-auto text-[10px] text-muted-foreground">Press Enter</span>
                                    </div>
                                )}

                                {filteredOptions.length === 0 && (!allowCustom || !search.trim()) ? (
                                    <p className="py-6 text-center text-sm text-muted-foreground">No results found.</p>
                                ) : (
                                    filteredOptions.map((option) => {
                                        const label = getOptionLabel(option)
                                        const val = getOptionValue(option)
                                        return (
                                            <div
                                                key={val}
                                                className={cn(
                                                    "relative flex w-full cursor-pointer select-none items-center rounded-sm px-2 py-2 text-sm outline-none hover:bg-primary/10 hover:text-primary transition-colors",
                                                )}
                                                onClick={(e) => {
                                                    e.stopPropagation()
                                                    handleSelect(val)
                                                }}
                                            >
                                                <Check className={cn("mr-2 h-4 w-4 opacity-0")} />
                                                {label}
                                            </div>
                                        )
                                    })
                                )}
                                {selectedValues.length > 0 && (
                                    <>
                                        <div className="h-px bg-border my-1" />
                                        <div className="px-2 py-1.5 text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                                            Selected
                                        </div>
                                        {selectedValues.map((val) => (
                                            <div
                                                key={`sel-${val}`}
                                                className="relative flex w-full cursor-default select-none items-center rounded-sm px-2 py-2 text-sm outline-none bg-primary/5 text-primary/80"
                                            >
                                                <Check className="mr-2 h-4 w-4 opacity-100" />
                                                {getItemLabel(val)}
                                            </div>
                                        ))}
                                    </>
                                )}
                            </div>
                        </div>
                    </>
                )}
            </div>
        </div>
    )
}
