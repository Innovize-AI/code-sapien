"use client"

import { useEffect, useRef, useState } from "react"
import { usePathname } from "next/navigation"

export function NavigationProgress() {
    const pathname = usePathname()
    const [width, setWidth] = useState(0)
    const [visible, setVisible] = useState(false)
    const prevPathname = useRef(pathname)
    const completeTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
    const hideTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

    const start = () => {
        clearTimeout(completeTimer.current)
        clearTimeout(hideTimer.current)
        setVisible(true)
        setWidth(0)
        // Jump to 15% immediately, then ease toward 80%
        requestAnimationFrame(() => {
            setWidth(15)
            setTimeout(() => setWidth(60), 100)
            setTimeout(() => setWidth(80), 500)
        })
    }

    const complete = () => {
        setWidth(100)
        completeTimer.current = setTimeout(() => {
            setVisible(false)
            setWidth(0)
        }, 350)
    }

    // Detect navigation start by intercepting <a> clicks
    useEffect(() => {
        const handleClick = (e: MouseEvent) => {
            const anchor = (e.target as HTMLElement).closest("a")
            if (!anchor) return
            const href = anchor.getAttribute("href")
            // Only intercept internal same-origin links
            if (!href || href.startsWith("http") || href.startsWith("#") || href.startsWith("mailto")) return
            if (anchor.target === "_blank") return
            start()
        }
        document.addEventListener("click", handleClick)
        return () => document.removeEventListener("click", handleClick)
    }, [])

    // Complete when pathname changes
    useEffect(() => {
        if (pathname !== prevPathname.current) {
            prevPathname.current = pathname
            complete()
        }
    }, [pathname])

    // Cleanup on unmount
    useEffect(() => () => {
        clearTimeout(completeTimer.current)
        clearTimeout(hideTimer.current)
    }, [])

    if (!visible) return null

    return (
        <div
            aria-hidden
            className="fixed top-0 left-0 z-[9999] h-[3px] bg-primary pointer-events-none"
            style={{
                width: `${width}%`,
                transition: width === 100
                    ? "width 200ms ease-out"
                    : width === 0
                    ? "none"
                    : "width 400ms ease-out",
            }}
        />
    )
}
