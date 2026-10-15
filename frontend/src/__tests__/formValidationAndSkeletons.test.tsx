import React from "react"
import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { useFormValidation, FormFieldError } from "../components/common/FormValidation"
import { EmptyState } from "../components/common/EmptyState"
import {
  IncidentListSkeleton,
  InvestigationTimelineSkeleton,
} from "../components/common/Skeletons"

const TestFormComponent: React.FC<{ onSubmit?: (data: Record<string, unknown>) => void }> = ({ onSubmit }) => {
  const { values, errors, setValue, setFieldTouched, validateAll } = useFormValidation(
    {
      serviceName: "",
      poolSize: "20",
    },
    {
      serviceName: { required: "Service name is required", minLength: { value: 3, message: "Min 3 chars" } },
      poolSize: { required: "Pool size is required" },
    }
  )

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (validateAll()) {
      onSubmit?.(values)
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <label htmlFor="service-name-input">Service</label>
      <input
        id="service-name-input"
        value={values.serviceName}
        onChange={(e) => setValue("serviceName", e.target.value)}
        onBlur={() => setFieldTouched("serviceName")}
        aria-invalid={!!errors.serviceName}
        aria-describedby={errors.serviceName ? "service-error" : undefined}
      />
      <FormFieldError id="service-error" error={errors.serviceName} />

      <label htmlFor="pool-size-input">Pool</label>
      <input
        id="pool-size-input"
        value={values.poolSize}
        onChange={(e) => setValue("poolSize", e.target.value)}
      />
      <FormFieldError id="pool-error" error={errors.poolSize} />

      <button type="submit">Submit Form</button>
    </form>
  )
}

describe("Form Validation and Skeletons", () => {
  describe("useFormValidation & FormFieldError", () => {
    it("validates required fields and shows accessible inline error", () => {
      render(<TestFormComponent />)

      const submitBtn = screen.getByRole("button", { name: /Submit Form/i })
      fireEvent.click(submitBtn)

      const input = screen.getByLabelText("Service")
      expect(input).toHaveAttribute("aria-invalid", "true")
      expect(screen.getByRole("alert")).toHaveTextContent("Service name is required")
    })

    it("preserves user input value across validation failures", () => {
      render(<TestFormComponent />)

      const input = screen.getByLabelText("Service")
      fireEvent.change(input, { target: { value: "ab" } }) // Too short (< 3)
      fireEvent.blur(input)

      expect(input).toHaveValue("ab")
      expect(screen.getByRole("alert")).toHaveTextContent("Min 3 chars")

      // User adds character to satisfy rule
      fireEvent.change(input, { target: { value: "abc" } })
      expect(screen.queryByRole("alert")).not.toBeInTheDocument()
      expect(input).toHaveValue("abc")
    })
  })

  describe("EmptyState Variants", () => {
    it("renders no-incidents operational state", () => {
      render(<EmptyState variant="no-incidents" />)
      expect(screen.getByText(/All Systems Operational/i)).toBeInTheDocument()
      expect(screen.getByText(/Zero active incidents detected/i)).toBeInTheDocument()
    })

    it("renders custom empty state with action trigger", () => {
      const onAction = vi.fn()
      render(
        <EmptyState
          title="Custom Empty View"
          description="Nothing to see here"
          actionLabel="Add Item"
          onAction={onAction}
        />
      )
      expect(screen.getByText("Custom Empty View")).toBeInTheDocument()
      fireEvent.click(screen.getByRole("button", { name: "Add Item" }))
      expect(onAction).toHaveBeenCalledTimes(1)
    })
  })

  describe("Skeletons", () => {
    it("renders incident list skeleton with status role", () => {
      render(<IncidentListSkeleton count={4} />)
      expect(screen.getByRole("status")).toBeInTheDocument()
    })

    it("renders investigation timeline skeleton", () => {
      render(<InvestigationTimelineSkeleton count={3} />)
      expect(screen.getByRole("status")).toBeInTheDocument()
    })
  })
})
