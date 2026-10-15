/* eslint-disable react-refresh/only-export-components */
import React, { useState, useCallback } from "react"
import { AlertCircle } from "lucide-react"
import { cn } from "../../lib/utils"

export interface ValidationError {
  field: string
  message: string
}

export interface FieldValidationRules {
  required?: boolean | string
  minLength?: { value: number; message: string }
  maxLength?: { value: number; message: string }
  pattern?: { regex: RegExp; message: string }
  validate?: (value: unknown) => string | null | undefined
}

export function useFormValidation<T extends Record<string, unknown>>(
  initialValues: T,
  rules: Partial<Record<keyof T, FieldValidationRules>> = {}
) {
  // Preserve user input across submissions and validation failures
  const [values, setValues] = useState<T>(initialValues)
  const [errors, setErrors] = useState<Partial<Record<keyof T, string>>>({})
  const [touched, setTouched] = useState<Partial<Record<keyof T, boolean>>>({})

  const validateField = useCallback(
    (field: keyof T, value: unknown): string | null => {
      const rule = rules[field]
      if (!rule) return null

      // Required check
      if (rule.required) {
        const isEmpty =
          value === undefined ||
          value === null ||
          (typeof value === "string" && value.trim() === "")
        if (isEmpty) {
          return typeof rule.required === "string" ? rule.required : "This field is required."
        }
      }

      // If empty and not required, skip format checks
      if (value === undefined || value === null || value === "") {
        return null
      }

      // Min length
      if (rule.minLength && typeof value === "string" && value.length < rule.minLength.value) {
        return rule.minLength.message
      }

      // Max length
      if (rule.maxLength && typeof value === "string" && value.length > rule.maxLength.value) {
        return rule.maxLength.message
      }

      // Pattern
      if (rule.pattern && typeof value === "string" && !rule.pattern.regex.test(value)) {
        return rule.pattern.message
      }

      // Custom validator
      if (rule.validate) {
        const customError = rule.validate(value)
        if (customError) return customError
      }

      return null
    },
    [rules]
  )

  const setValue = useCallback(
    (field: keyof T, value: unknown) => {
      setValues((prev) => ({ ...prev, [field]: value }))
      // Clear error immediately when user begins correcting
      if (errors[field]) {
        setErrors((prev) => {
          const next = { ...prev }
          delete next[field]
          return next
        })
      }
    },
    [errors]
  )

  const setFieldTouched = useCallback(
    (field: keyof T) => {
      setTouched((prev) => ({ ...prev, [field]: true }))
      const err = validateField(field, values[field])
      if (err) {
        setErrors((prev) => ({ ...prev, [field]: err }))
      }
    },
    [validateField, values]
  )

  const validateAll = useCallback((): boolean => {
    const newErrors: Partial<Record<keyof T, string>> = {}
    let isValid = true

    for (const key of Object.keys(rules) as (keyof T)[]) {
      const err = validateField(key, values[key])
      if (err) {
        newErrors[key] = err
        isValid = false
      }
    }

    setErrors(newErrors)
    // Mark all validated fields as touched
    const allTouched: Partial<Record<keyof T, boolean>> = {}
    for (const key of Object.keys(rules) as (keyof T)[]) {
      allTouched[key] = true
    }
    setTouched(allTouched)

    return isValid
  }, [rules, validateField, values])

  const reset = useCallback(
    (newValues?: T) => {
      setValues(newValues || initialValues)
      setErrors({})
      setTouched({})
    },
    [initialValues]
  )

  return {
    values,
    errors,
    touched,
    setValue,
    setFieldTouched,
    validateAll,
    reset,
    isValid: Object.keys(errors).length === 0,
  }
}

/**
 * Accessible Inline Field Error message
 */
export const FormFieldError: React.FC<{
  id: string
  error?: string
  className?: string
}> = ({ id, error, className }) => {
  if (!error) return null

  return (
    <div
      id={id}
      role="alert"
      aria-live="assertive"
      className={cn("flex items-center gap-1.5 text-vermilion text-[11px] font-sans mt-1", className)}
    >
      <AlertCircle className="w-3.5 h-3.5 shrink-0" />
      <span>{error}</span>
    </div>
  )
}
