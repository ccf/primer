import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"

export function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <p className="text-6xl font-bold text-muted-foreground/30">404</p>
      <p className="mt-4 text-lg text-muted-foreground">Page not found</p>
      <Link to="/" className="mt-6">
        <Button variant="outline">Go to Overview</Button>
      </Link>
    </div>
  )
}
