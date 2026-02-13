export interface AuthUser {
  engineer_id: string
  name: string
  email: string
  role: string
  team_id: string | null
  avatar_url: string | null
  github_username: string | null
  display_name: string | null
}
