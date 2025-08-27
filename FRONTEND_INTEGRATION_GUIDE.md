# 🚀 Frontend Integration Guide

**Canvas-to-Notion Sync API with Firebase Authentication**

This guide explains how to integrate the backend API with a TypeScript/Next.js frontend application. The backend is currently running on localhost and includes Firebase authentication with Google OAuth.

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [API Base Configuration](#api-base-configuration)
3. [Authentication Flow](#authentication-flow)
4. [API Endpoints Reference](#api-endpoints-reference)
5. [TypeScript Types](#typescript-types)
6. [Next.js Implementation](#nextjs-implementation)
7. [Error Handling](#error-handling)
8. [State Management](#state-management)
9. [Example Components](#example-components)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
npm install firebase @types/firebase
# or
yarn add firebase @types/firebase
```

### 2. Environment Variables

Create `.env.local` in your Next.js project:

```bash
# Backend API (currently localhost)
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Firebase Config (get from /auth/firebase-config endpoint)
NEXT_PUBLIC_FIREBASE_API_KEY=your_api_key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your_project_id
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your_bucket
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=your_sender_id
NEXT_PUBLIC_FIREBASE_APP_ID=your_app_id
NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID=your_measurement_id
```

### 3. Basic Setup

```typescript
// lib/firebase.ts
import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
  measurementId: process.env.NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID,
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
```

## 🔧 API Base Configuration

```typescript
// lib/api.ts
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export const apiClient = {
  baseURL: API_BASE_URL,

  async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;

    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: "Network error" }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  },

  // Helper methods
  get: <T>(endpoint: string) => this.request<T>(endpoint),

  post: <T>(endpoint: string, data: any) =>
    this.request<T>(endpoint, {
      method: "POST",
      body: JSON.stringify(data),
    }),
};
```

## 🔑 Authentication Flow

### 1. Google OAuth Login

```typescript
// lib/auth.ts
import { signInWithPopup, getIdToken, signOut } from "firebase/auth";
import { auth, googleProvider } from "./firebase";
import { apiClient } from "./api";

export interface AuthUser {
  user_email: string;
  user_id: string;
  display_name?: string;
  photo_url?: string;
  access_token: string;
  token_type: string;
  expires_in: number;
}

export class AuthService {
  private static instance: AuthService;
  private currentUser: AuthUser | null = null;

  static getInstance(): AuthService {
    if (!AuthService.instance) {
      AuthService.instance = new AuthService();
    }
    return AuthService.instance;
  }

  async loginWithGoogle(): Promise<AuthUser> {
    try {
      // 1. Google OAuth popup
      const result = await signInWithPopup(auth, googleProvider);

      // 2. Get Firebase ID token
      const idToken = await getIdToken(result.user);

      // 3. Exchange for JWT from backend
      const authData = await apiClient.post<AuthUser>("/auth/login", {
        id_token: idToken,
      });

      // 4. Store user data
      this.currentUser = authData;
      localStorage.setItem("access_token", authData.access_token);
      localStorage.setItem("user_data", JSON.stringify(authData));

      return authData;
    } catch (error) {
      console.error("Login failed:", error);
      throw error;
    }
  }

  async logout(): Promise<void> {
    try {
      // 1. Call backend logout (for audit logging)
      if (this.currentUser?.access_token) {
        await apiClient.post("/auth/logout", { revoke_token: true });
      }

      // 2. Sign out from Firebase
      await signOut(auth);

      // 3. Clear local data
      this.currentUser = null;
      localStorage.removeItem("access_token");
      localStorage.removeItem("user_data");
    } catch (error) {
      console.error("Logout failed:", error);
    }
  }

  getCurrentUser(): AuthUser | null {
    if (!this.currentUser) {
      const stored = localStorage.getItem("user_data");
      if (stored) {
        this.currentUser = JSON.parse(stored);
      }
    }
    return this.currentUser;
  }

  getAccessToken(): string | null {
    return localStorage.getItem("access_token");
  }

  isAuthenticated(): boolean {
    return !!this.getAccessToken();
  }
}

export const authService = AuthService.getInstance();
```

### 2. Authenticated API Client

```typescript
// lib/authenticatedApi.ts
import { apiClient } from "./api";
import { authService } from "./auth";

export const authenticatedApiClient = {
  async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = authService.getAccessToken();

    if (!token) {
      throw new Error("Authentication required");
    }

    return apiClient.request<T>(endpoint, {
      ...options,
      headers: {
        ...options.headers,
        Authorization: `Bearer ${token}`,
      },
    });
  },

  get: <T>(endpoint: string) => this.request<T>(endpoint),

  post: <T>(endpoint: string, data: any) =>
    this.request<T>(endpoint, {
      method: "POST",
      body: JSON.stringify(data),
    }),
};
```

## 📡 API Endpoints Reference

### Authentication Endpoints

#### `GET /auth/firebase-config`

Get Firebase configuration for frontend initialization.

```typescript
// No authentication required
const config = await apiClient.get<{ firebase: any }>("/auth/firebase-config");
```

#### `POST /auth/login`

Authenticate user with Firebase ID token.

```typescript
interface LoginRequest {
  id_token: string;
}

interface LoginResponse {
  success: boolean;
  message: string;
  user_email: string;
  user_id: string;
  display_name?: string;
  photo_url?: string;
  access_token: string;
  token_type: string;
  expires_in: number;
}

const response = await apiClient.post<LoginResponse>("/auth/login", {
  id_token: firebaseIdToken,
});
```

#### `GET /auth/me`

Get current authenticated user information.

```typescript
interface UserProfile {
  success: boolean;
  user_email: string;
  user_id: string;
  display_name?: string;
  photo_url?: string;
  settings: any;
  preferences: any;
  setup_status: {
    has_canvas: boolean;
    has_notion: boolean;
    has_google: boolean;
  };
}

const profile = await authenticatedApiClient.get<UserProfile>("/auth/me");
```

#### `POST /auth/logout`

Logout current user (audit logging).

```typescript
interface LogoutRequest {
  revoke_token: boolean;
}

interface LogoutResponse {
  success: boolean;
  message: string;
  note: string;
}

const response = await authenticatedApiClient.post<LogoutResponse>(
  "/auth/logout",
  {
    revoke_token: false,
  }
);
```

### Setup Endpoints

#### `POST /setup/init`

Initialize user setup with Canvas and Notion credentials.

```typescript
interface InitSetupRequest {
  user_email: string;
  canvas_base_url: string;
  notion_token: string;
  notion_parent_page_id: string;
}

interface SetupResponse {
  success: boolean;
  message: string;
  user_email: string;
  next_step: string;
}

const response = await authenticatedApiClient.post<SetupResponse>(
  "/setup/init",
  {
    user_email: "user@example.com",
    canvas_base_url: "https://your-institution.instructure.com",
    notion_token: "your_notion_integration_token",
    notion_parent_page_id: "your_notion_parent_page_id",
  }
);
```

#### `POST /setup/canvas/pat`

Save Canvas Personal Access Token.

```typescript
interface CanvasPATRequest {
  canvas_pat: string;
}

interface CanvasPATResponse {
  success: boolean;
  message: string;
  next_step: string;
}

const response = await authenticatedApiClient.post<CanvasPATResponse>(
  "/setup/canvas/pat",
  {
    canvas_pat: "your_canvas_personal_access_token",
  }
);
```

#### `GET /setup/me`

Get current setup status.

```typescript
interface SetupStatusResponse {
  user_email: string;
  has_canvas: boolean;
  has_notion: boolean;
  has_google: boolean;
  last_canvas_sync?: string;
  last_notion_sync?: string;
  last_google_sync?: string;
  last_assignment_sync?: string;
  setup_complete: boolean;
  next_steps: string[];
}

const status = await authenticatedApiClient.get<SetupStatusResponse>(
  "/setup/me"
);
```

### Sync Endpoints

#### `POST /sync/start`

Start Canvas to Notion course synchronization.

```typescript
interface SyncStartRequest {
  user_email: string;
}

interface CanvasSyncResponse {
  success: boolean;
  message: string;
  courses_found: number;
  courses_created: number;
  courses_failed: number;
  courses_skipped: number;
  created_courses: any[];
  failed_courses: any[];
  note: string;
}

const response = await authenticatedApiClient.post<CanvasSyncResponse>(
  "/sync/start",
  {
    user_email: "user@example.com",
  }
);
```

#### `POST /sync/assignments`

Sync Canvas assignments to Notion.

```typescript
interface AssignmentSyncRequest {
  user_email: string;
}

interface AssignmentSyncResponse {
  success: boolean;
  message: string;
  courses_processed: number;
  assignments_found: number;
  assignments_created: number;
  assignments_failed: number;
  assignments_skipped: number;
  created_assignments: any[];
  failed_assignments: any[];
  note: string;
}

const response = await authenticatedApiClient.post<AssignmentSyncResponse>(
  "/sync/assignments",
  {
    user_email: "user@example.com",
  }
);
```

#### `GET /sync/courses`

Get all synced courses.

```typescript
interface SyncedCoursesResponse {
  success: boolean;
  message: string;
  courses_count: number;
  courses: any[];
  note: string;
}

const courses = await authenticatedApiClient.get<SyncedCoursesResponse>(
  "/sync/courses"
);
```

#### `GET /sync/assignments`

Get all synced assignments.

```typescript
interface SyncedAssignmentsResponse {
  success: boolean;
  message: string;
  assignments_count: number;
  assignments: any[];
  note: string;
}

const assignments = await authenticatedApiClient.get<SyncedAssignmentsResponse>(
  "/sync/assignments"
);
```

#### `GET /sync/status`

Get overall sync status.

```typescript
interface SyncStatusResponse {
  success: boolean;
  user_email: string;
  setup_status: {
    has_canvas: boolean;
    has_notion: boolean;
  };
  sync_history: {
    last_course_sync?: string;
    last_assignment_sync?: string;
  };
  sync_data: {
    courses_synced: number;
    assignments_synced: number;
  };
  courses: any[];
  assignments: any[];
  recent_sync_logs: any[];
  note: string;
}

const status = await authenticatedApiClient.get<SyncStatusResponse>(
  "/sync/status"
);
```

#### `GET /sync/logs`

Get sync logs.

```typescript
interface SyncLogsResponse {
  success: boolean;
  message: string;
  logs_count: number;
  logs: any[];
  note: string;
}

const logs = await authenticatedApiClient.get<SyncLogsResponse>(
  "/sync/logs?limit=20"
);
```

#### `GET /sync/audit`

Get audit logs.

```typescript
interface AuditLogsResponse {
  success: boolean;
  message: string;
  logs_count: number;
  logs: any[];
  note: string;
}

const audit = await authenticatedApiClient.get<AuditLogsResponse>(
  "/sync/audit?limit=50"
);
```

### Canvas Endpoints

#### `POST /canvas/test`

Test Canvas API connection.

```typescript
interface CanvasTestRequest {
  canvas_base_url: string;
  canvas_pat: string;
}

interface CanvasTestResponse {
  success: boolean;
  message: string;
  user_info: any;
}

const response = await apiClient.post<CanvasTestResponse>("/canvas/test", {
  canvas_base_url: "https://your-institution.instructure.com",
  canvas_pat: "your_canvas_pat",
});
```

#### `POST /canvas/inspect`

Inspect Canvas courses.

```typescript
interface CanvasInspectionResponse {
  success: boolean;
  message: string;
  courses_found: number;
  courses: any[];
  note: string;
}

const inspection = await authenticatedApiClient.post<CanvasInspectionResponse>(
  "/canvas/inspect"
);
```

### Notion Endpoints

#### `POST /notion/schemas`

Get Notion database schemas.

```typescript
interface NotionSchemaRequest {
  notion_token: string;
  notion_parent_page_id: string;
}

interface NotionSchemaResponse {
  success: boolean;
  databases_found: number;
  schemas: any;
  message: string;
}

const schemas = await apiClient.post<NotionSchemaResponse>("/notion/schemas", {
  notion_token: "your_notion_token",
  notion_parent_page_id: "your_parent_page_id",
});
```

## 📝 TypeScript Types

```typescript
// types/api.ts

// Base API Response
export interface ApiResponse<T = any> {
  success: boolean;
  message: string;
  data?: T;
}

// User Types
export interface User {
  user_email: string;
  user_id: string;
  display_name?: string;
  photo_url?: string;
}

export interface UserSettings {
  canvas_base_url?: string;
  canvas_pat?: string;
  notion_token?: string;
  notion_parent_page_id?: string;
  last_canvas_sync?: string;
  last_notion_sync?: string;
  last_assignment_sync?: string;
  created_at?: string;
  updated_at?: string;
}

export interface UserPreferences {
  dashboard_layout: "grid" | "list";
  default_view: "assignments" | "courses" | "dashboard";
  notifications_enabled: boolean;
  theme: "light" | "dark";
  sync_frequency: "manual" | "hourly" | "daily";
  show_completed_assignments: boolean;
  show_past_assignments: boolean;
  assignments_per_page: number;
}

// Sync Types
export interface SyncLog {
  id?: string;
  user_email: string;
  sync_type: "courses" | "assignments" | "canvas_test" | "notion_test";
  status: "success" | "failed" | "partial";
  items_processed: number;
  items_created: number;
  items_failed: number;
  items_skipped: number;
  duration_ms?: number;
  error_message?: string;
  metadata?: any;
  timestamp?: string;
}

export interface AuditLog {
  id?: string;
  user_email: string;
  action: "create" | "update" | "delete" | "sync" | "login" | "logout";
  resource_type: "course" | "assignment" | "user_settings";
  target_id: string;
  old_value?: any;
  new_value?: any;
  metadata?: any;
  timestamp?: string;
}

// Canvas Types
export interface CanvasCourse {
  id: number;
  name: string;
  course_code: string;
  start_at?: string;
  end_at?: string;
  enrollment_state: string;
  total_students: number;
  teachers?: any[];
}

export interface CanvasAssignment {
  id: number;
  name: string;
  description?: string;
  due_at?: string;
  points_possible: number;
  assignment_group_id: number;
  course_id: number;
  submission_types: string[];
  grading_type: string;
}

// Notion Types
export interface NotionDatabase {
  id: string;
  title: string;
  properties: any;
  url: string;
}

export interface NotionPage {
  id: string;
  properties: any;
  url: string;
}
```

## ⚛️ Next.js Implementation

### 1. Authentication Context

```typescript
// contexts/AuthContext.tsx
"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { authService, AuthUser } from "@/lib/auth";

interface AuthContextType {
  user: AuthUser | null;
  loading: boolean;
  login: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for existing user on mount
    const currentUser = authService.getCurrentUser();
    if (currentUser) {
      setUser(currentUser);
    }
    setLoading(false);
  }, []);

  const login = async () => {
    try {
      const authUser = await authService.loginWithGoogle();
      setUser(authUser);
    } catch (error) {
      console.error("Login failed:", error);
      throw error;
    }
  };

  const logout = async () => {
    await authService.logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
```

### 2. Protected Route Component

```typescript
// components/ProtectedRoute.tsx
"use client";

import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

interface ProtectedRouteProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export function ProtectedRoute({ children, fallback }: ProtectedRouteProps) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [user, loading, router]);

  if (loading) {
    return fallback || <div>Loading...</div>;
  }

  if (!user) {
    return null;
  }

  return <>{children}</>;
}
```

### 3. API Hooks

```typescript
// hooks/useApi.ts
import { useState, useCallback } from "react";
import { authenticatedApiClient } from "@/lib/authenticatedApi";

interface UseApiOptions<T> {
  onSuccess?: (data: T) => void;
  onError?: (error: Error) => void;
}

export function useApi<T = any>(options: UseApiOptions<T> = {}) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const execute = useCallback(
    async (endpoint: string, method: "GET" | "POST" = "GET", body?: any) => {
      setLoading(true);
      setError(null);

      try {
        let result: T;

        if (method === "GET") {
          result = await authenticatedApiClient.get<T>(endpoint);
        } else {
          result = await authenticatedApiClient.post<T>(endpoint, body);
        }

        setData(result);
        options.onSuccess?.(result);
        return result;
      } catch (err) {
        const error = err instanceof Error ? err : new Error("Unknown error");
        setError(error);
        options.onError?.(error);
        throw error;
      } finally {
        setLoading(false);
      }
    },
    [options]
  );

  return {
    data,
    loading,
    error,
    execute,
    reset: () => {
      setData(null);
      setError(null);
    },
  };
}
```

### 4. Dashboard Page Example

```typescript
// app/dashboard/page.tsx
"use client";

import { useAuth } from "@/contexts/AuthContext";
import { useApi } from "@/hooks/useApi";
import { SyncStatusResponse } from "@/types/api";
import { useEffect } from "react";

export default function DashboardPage() {
  const { user } = useAuth();
  const {
    data: status,
    loading,
    error,
    execute,
  } = useApi<SyncStatusResponse>();

  useEffect(() => {
    if (user) {
      execute("/sync/status");
    }
  }, [user, execute]);

  if (loading) return <div>Loading dashboard...</div>;
  if (error) return <div>Error: {error.message}</div>;
  if (!status) return <div>No data available</div>;

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-2">Courses</h3>
          <p className="text-3xl font-bold text-blue-600">
            {status.sync_data.courses_synced}
          </p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-2">Assignments</h3>
          <p className="text-3xl font-bold text-green-600">
            {status.sync_data.assignments_synced}
          </p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-2">Last Sync</h3>
          <p className="text-sm text-gray-600">
            {status.sync_history.last_assignment_sync
              ? new Date(
                  status.sync_history.last_assignment_sync
                ).toLocaleDateString()
              : "Never"}
          </p>
        </div>
      </div>

      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
        <div className="space-y-2">
          {status.recent_sync_logs.map((log, index) => (
            <div
              key={index}
              className="flex justify-between items-center py-2 border-b"
            >
              <span className="capitalize">{log.sync_type}</span>
              <span
                className={`px-2 py-1 rounded text-xs ${
                  log.status === "success"
                    ? "bg-green-100 text-green-800"
                    : log.status === "failed"
                    ? "bg-red-100 text-red-800"
                    : "bg-yellow-100 text-yellow-800"
                }`}
              >
                {log.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

### 5. Login Page Example

```typescript
// app/login/page.tsx
"use client";

import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function LoginPage() {
  const { user, login, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (user) {
      router.push("/dashboard");
    }
  }, [user, router]);

  const handleLogin = async () => {
    try {
      await login();
      router.push("/dashboard");
    } catch (error) {
      console.error("Login failed:", error);
      // Handle error (show toast, etc.)
    }
  };

  if (loading) return <div>Loading...</div>;
  if (user) return null;

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Sign in to Canvas Sync
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Synchronize your Canvas courses with Notion
          </p>
        </div>

        <div>
          <button
            onClick={handleLogin}
            className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
              <path
                fill="currentColor"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="currentColor"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="currentColor"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              />
              <path
                fill="currentColor"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
            Sign in with Google
          </button>
        </div>
      </div>
    </div>
  );
}
```

## 🚨 Error Handling

```typescript
// lib/errorHandler.ts
export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public code?: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function handleApiError(error: any): never {
  if (error instanceof ApiError) {
    throw error;
  }

  if (error.response) {
    // HTTP error response
    const statusCode = error.response.status;
    const message = error.response.data?.detail || "Request failed";
    throw new ApiError(message, statusCode);
  }

  if (error.request) {
    // Network error
    throw new ApiError("Network error - no response received", 0);
  }

  // Other error
  throw new ApiError(error.message || "Unknown error", 0);
}

// Usage in components
try {
  await execute("/sync/start");
} catch (error) {
  if (error instanceof ApiError) {
    if (error.statusCode === 401) {
      // Handle authentication error
      router.push("/login");
    } else {
      // Show error message
      toast.error(error.message);
    }
  } else {
    // Handle other errors
    toast.error("An unexpected error occurred");
  }
}
```

## 📊 State Management

### 1. Zustand Store Example

```typescript
// stores/syncStore.ts
import { create } from "zustand";
import { SyncStatusResponse, SyncLog, AuditLog } from "@/types/api";

interface SyncState {
  status: SyncStatusResponse | null;
  logs: SyncLog[];
  auditLogs: AuditLog[];
  loading: boolean;
  error: string | null;

  // Actions
  fetchStatus: () => Promise<void>;
  fetchLogs: (limit?: number) => Promise<void>;
  fetchAuditLogs: (limit?: number) => Promise<void>;
  clearError: () => void;
}

export const useSyncStore = create<SyncState>((set, get) => ({
  status: null,
  logs: [],
  auditLogs: [],
  loading: false,
  error: null,

  fetchStatus: async () => {
    set({ loading: true, error: null });
    try {
      const response = await authenticatedApiClient.get<SyncStatusResponse>(
        "/sync/status"
      );
      set({ status: response, loading: false });
    } catch (error) {
      set({ error: error.message, loading: false });
    }
  },

  fetchLogs: async (limit = 20) => {
    set({ loading: true, error: null });
    try {
      const response = await authenticatedApiClient.get<{ logs: SyncLog[] }>(
        `/sync/logs?limit=${limit}`
      );
      set({ logs: response.logs, loading: false });
    } catch (error) {
      set({ error: error.message, loading: false });
    }
  },

  fetchAuditLogs: async (limit = 50) => {
    set({ loading: true, error: null });
    try {
      const response = await authenticatedApiClient.get<{ logs: AuditLog[] }>(
        `/sync/audit?limit=${limit}`
      );
      set({ auditLogs: response.logs, loading: false });
    } catch (error) {
      set({ error: error.message, loading: false });
    }
  },

  clearError: () => set({ error: null }),
}));
```

### 2. React Query Example

```typescript
// hooks/useSyncQueries.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { authenticatedApiClient } from "@/lib/authenticatedApi";
import {
  SyncStatusResponse,
  CanvasSyncResponse,
  AssignmentSyncResponse,
} from "@/types/api";

export function useSyncStatus() {
  return useQuery({
    queryKey: ["sync", "status"],
    queryFn: () =>
      authenticatedApiClient.get<SyncStatusResponse>("/sync/status"),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useSyncCourses() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userEmail: string) =>
      authenticatedApiClient.post<CanvasSyncResponse>("/sync/start", {
        user_email: userEmail,
      }),
    onSuccess: () => {
      // Invalidate and refetch status
      queryClient.invalidateQueries({ queryKey: ["sync", "status"] });
    },
  });
}

export function useSyncAssignments() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userEmail: string) =>
      authenticatedApiClient.post<AssignmentSyncResponse>("/sync/assignments", {
        user_email: userEmail,
      }),
    onSuccess: () => {
      // Invalidate and refetch status
      queryClient.invalidateQueries({ queryKey: ["sync", "status"] });
    },
  });
}
```

## 🔧 Development Setup

### 1. Start Backend

```bash
# In your backend directory
cd /path/to/your/backend
python -m uvicorn app.main:app --reload --port 8000
```

### 2. Start Frontend

```bash
# In your Next.js project
npm run dev
# or
yarn dev
```

### 3. Test Authentication

1. Navigate to `/login`
2. Click "Sign in with Google"
3. Complete OAuth flow
4. Verify redirect to `/dashboard`

### 4. Test API Endpoints

Use the dashboard to test:

- Setup initialization
- Canvas connection testing
- Course synchronization
- Assignment synchronization

## 📱 Mobile Considerations

The API is designed to work seamlessly with mobile apps:

- **JWT tokens** for stateless authentication
- **RESTful endpoints** for easy mobile integration
- **Real-time capabilities** via Firebase
- **Offline support** with Firebase Firestore
- **Push notifications** ready (Firebase Cloud Messaging)

## 🚀 Production Deployment

When ready for production:

1. **Set up Firebase project** with proper authentication rules
2. **Configure environment variables** for production
3. **Update API base URL** to production domain
4. **Enable Firebase security rules** for Firestore
5. **Set up monitoring** and error tracking
6. **Configure CORS** for production domains

## 📚 Additional Resources

- [Firebase Documentation](https://firebase.google.com/docs)
- [Next.js Authentication](https://nextjs.org/docs/authentication)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [React Query Documentation](https://tanstack.com/query/latest)

---

**🎉 Your frontend is now ready to integrate with the Firebase-powered Canvas-to-Notion sync backend!**

The API provides everything needed for a modern, real-time dashboard with Google authentication, comprehensive logging, and seamless Canvas/Notion synchronization.
