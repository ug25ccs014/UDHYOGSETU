'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Loader2 } from 'lucide-react'
import { useCreateProject, useAnalyzeProject } from '@/hooks/useApi'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'

const steps = ['Business', 'Project', 'Location', 'Operations', 'Review']

const stepRequiredFields: Record<number, string[]> = {
  0: ['company_name', 'business_type', 'industry', 'sector'],
  1: ['project_name', 'project_stage'],
  2: ['location_district', 'location_city', 'land_type'],
  3: ['production_type', 'building_type'],
}

export default function OnboardingWizard() {
  const router = useRouter()
  const [currentStep, setCurrentStep] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [stepError, setStepError] = useState<string | null>(null)
  const [formData, setFormData] = useState({
    company_name: '',
    business_type: '',
    industry: '',
    sector: '',
    project_name: '',
    is_new: true,
    project_stage: '',
    investment_amount: 0,
    location_state: 'Maharashtra',
    location_district: '',
    location_city: '',
    location_industrial_area: '',
    location_midc_estate: '',
    land_type: '',
    employees: 0,
    production_type: '',
    hazardous_materials: false,
    has_boiler: false,
    electricity_load: 0,
    water_consumption: 0,
    pollution_potential: 'low',
    building_type: '',
  })

  const createProject = useCreateProject()
  const analyzeProject = useAnalyzeProject()
  const loading = createProject.isPending || analyzeProject.isPending

  const handleChange = (e: any) => {
    const { name, value, type, checked } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]:
        type === 'checkbox' ? checked : type === 'number' ? parseFloat(value) : value,
    }))
  }

  const handleToggle = (value: boolean) => {
    setFormData((prev) => ({ ...prev, is_new: value }))
  }

  const handleNext = () => {
    const missing = (stepRequiredFields[currentStep] || []).filter((field: string) => {
      const value = formData[field as keyof typeof formData]
      if (field === 'investment_amount') return Number(value) <= 0
      return typeof value === 'string' ? value.trim() === '' : !value
    })

    if (missing.length > 0) {
      setStepError(`Please fill in the required fields: ${missing.join(', ').replace(/_/g, ' ')}`)
      return
    }
    setStepError(null)
    if (currentStep < 4) setCurrentStep(currentStep + 1)
  }

  const handlePrev = () => {
    if (currentStep > 0) setCurrentStep(currentStep - 1)
  }

  const handleSubmit = async () => {
    setError(null)
    try {
      const project = await createProject.mutateAsync(formData)
      await analyzeProject.mutateAsync(project.id)
      router.push(`/dashboard/${project.id}/approvals`)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create project. Please try again.')
    }
  }

  const inputClass =
    'mt-1 w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
  const labelClass = 'block text-sm font-medium text-gray-700'

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Start New Project</h1>
        <p className="mt-2 text-gray-600">
          Let's set up your industrial project. Answer a few questions to build your approval roadmap.
        </p>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg shadow-sm">
        <div className="p-6 border-b">
          <div className="flex justify-between gap-1 sm:gap-4 mb-4">
            {steps.map((label, idx) => (
              <div key={idx} className="text-center flex-1 min-w-0">
                <div
                  aria-label={`Step ${idx + 1}: ${label}`}
                  className={`w-8 h-8 sm:w-9 sm:h-9 rounded-full flex items-center justify-center mx-auto text-sm sm:text-base transition ${
                    idx <= currentStep ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-600'
                  }`}
                >
                  {idx + 1}
                </div>
                <div className={`hidden sm:block text-xs mt-1.5 truncate ${idx <= currentStep ? 'text-blue-600 font-medium' : 'text-gray-500'}`}>
                  {label}
                </div>
              </div>
            ))}
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all"
              style={{ width: `${((currentStep + 1) / 5) * 100}%` }}
            />
          </div>
        </div>

        <div className="p-8">
          {(error || stepError) && (
            <div className="mb-6 p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">
              {error || stepError}
            </div>
          )}

          {currentStep === 0 && (
            <div className="space-y-6">
              <div>
                <label className={labelClass}>Company Name *</label>
                <Input
                  name="company_name"
                  value={formData.company_name}
                  onChange={handleChange}
                  placeholder="Enter your company name"
                />
              </div>
              <div>
                <label className={labelClass}>Business Type *</label>
                <Select name="business_type" value={formData.business_type} onChange={handleChange}>
                  <option value="">Select business type</option>
                  <option value="Manufacturing">Manufacturing</option>
                  <option value="Trading">Trading</option>
                  <option value="Service">Service</option>
                  <option value="Agriculture">Agriculture</option>
                </Select>
              </div>
              <div>
                <label className={labelClass}>Industry *</label>
                <Select name="industry" value={formData.industry} onChange={handleChange}>
                  <option value="">Select industry</option>
                  <option value="Textile">Textile</option>
                  <option value="Chemicals">Chemicals</option>
                  <option value="Pharmaceuticals">Pharmaceuticals</option>
                  <option value="Auto Components">Auto Components</option>
                  <option value="Food Processing">Food Processing</option>
                  <option value="Electronics">Electronics</option>
                  <option value="Steel">Steel</option>
                  <option value="Other">Other</option>
                </Select>
              </div>
              <div>
                <label className={labelClass}>Sector *</label>
                <Input
                  name="sector"
                  value={formData.sector}
                  onChange={handleChange}
                  placeholder="e.g., Heavy, Medium, Small"
                />
              </div>
            </div>
          )}

          {currentStep === 1 && (
            <div className="space-y-6">
              <div>
                <label className={labelClass}>Project Name *</label>
                <Input
                  name="project_name"
                  value={formData.project_name}
                  onChange={handleChange}
                  placeholder="Enter project name"
                />
              </div>
              <div>
                <label className={labelClass}>Project Type *</label>
                <div className="mt-2 space-y-2">
                  <label className="flex items-center cursor-pointer">
                    <input
                      type="radio"
                      checked={formData.is_new === true}
                      onChange={() => handleToggle(true)}
                      className="mr-2 accent-blue-600"
                    />
                    <span className="text-sm text-gray-700">New Project</span>
                  </label>
                  <label className="flex items-center cursor-pointer">
                    <input
                      type="radio"
                      checked={formData.is_new === false}
                      onChange={() => handleToggle(false)}
                      className="mr-2 accent-blue-600"
                    />
                    <span className="text-sm text-gray-700">Expansion / Modification</span>
                  </label>
                </div>
              </div>
              <div>
                <label className={labelClass}>Project Stage *</label>
                <Select name="project_stage" value={formData.project_stage} onChange={handleChange}>
                  <option value="">Select stage</option>
                  <option value="Planning">Planning</option>
                  <option value="Design">Design</option>
                  <option value="Pre-Implementation">Pre-Implementation</option>
                  <option value="Implementation">Implementation</option>
                </Select>
              </div>
              <div>
                <label className={labelClass}>Investment Amount (₹) *</label>
                <Input
                  type="number"
                  name="investment_amount"
                  value={formData.investment_amount}
                  onChange={handleChange}
                  placeholder="Enter investment in rupees"
                />
              </div>
            </div>
          )}

          {currentStep === 2 && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className={labelClass}>State *</label>
                  <Select name="location_state" value={formData.location_state} onChange={handleChange}>
                    <option value="Maharashtra">Maharashtra</option>
                    <option value="Gujarat">Gujarat</option>
                    <option value="Karnataka">Karnataka</option>
                  </Select>
                </div>
                <div>
                  <label className={labelClass}>District *</label>
                  <Input
                    name="location_district"
                    value={formData.location_district}
                    onChange={handleChange}
                    placeholder="e.g., Pune, Nagpur"
                  />
                </div>
              </div>
              <div>
                <label className={labelClass}>City *</label>
                <Input
                  name="location_city"
                  value={formData.location_city}
                  onChange={handleChange}
                  placeholder="Enter city name"
                />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className={labelClass}>Industrial Area</label>
                  <Input
                    name="location_industrial_area"
                    value={formData.location_industrial_area}
                    onChange={handleChange}
                    placeholder="Enter industrial area name"
                  />
                </div>
                <div>
                  <label className={labelClass}>MIDC Estate</label>
                  <Input
                    name="location_midc_estate"
                    value={formData.location_midc_estate}
                    onChange={handleChange}
                    placeholder="Enter MIDC estate name"
                  />
                </div>
              </div>
              <div>
                <label className={labelClass}>Land Type *</label>
                <Select name="land_type" value={formData.land_type} onChange={handleChange}>
                  <option value="">Select land type</option>
                  <option value="Own">Own</option>
                  <option value="Leased">Leased</option>
                  <option value="Government">Government</option>
                </Select>
              </div>
            </div>
          )}

          {currentStep === 3 && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className={labelClass}>Number of Employees *</label>
                  <Input
                    type="number"
                    name="employees"
                    value={formData.employees}
                    onChange={handleChange}
                    placeholder="e.g. 25"
                  />
                </div>
                <div>
                  <label className={labelClass}>Production Type *</label>
                  <Input
                    name="production_type"
                    value={formData.production_type}
                    onChange={handleChange}
                    placeholder="e.g., Batch, Continuous"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <label className="flex items-center p-3 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50">
                  <input
                    type="checkbox"
                    name="hazardous_materials"
                    checked={formData.hazardous_materials}
                    onChange={handleChange}
                    className="mr-3 w-4 h-4 accent-blue-600"
                  />
                  <span className="text-sm font-medium text-gray-700">Uses Hazardous Materials</span>
                </label>
                <label className="flex items-center p-3 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50">
                  <input
                    type="checkbox"
                    name="has_boiler"
                    checked={formData.has_boiler}
                    onChange={handleChange}
                    className="mr-3 w-4 h-4 accent-blue-600"
                  />
                  <span className="text-sm font-medium text-gray-700">Has Boiler Equipment</span>
                </label>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className={labelClass}>Electricity Load (kW)</label>
                  <Input
                    type="number"
                    name="electricity_load"
                    value={formData.electricity_load}
                    onChange={handleChange}
                    placeholder="Enter in kW"
                  />
                </div>
                <div>
                  <label className={labelClass}>Water Consumption (m³/day)</label>
                  <Input
                    type="number"
                    name="water_consumption"
                    value={formData.water_consumption}
                    onChange={handleChange}
                    placeholder="Enter in cubic meters per day"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className={labelClass}>Pollution Potential *</label>
                  <Select name="pollution_potential" value={formData.pollution_potential} onChange={handleChange}>
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </Select>
                </div>
                <div>
                  <label className={labelClass}>Building Type *</label>
                  <Select name="building_type" value={formData.building_type} onChange={handleChange}>
                    <option value="">Select building type</option>
                    <option value="Factory">Factory / Industrial Plant</option>
                    <option value="Office">Office / Commercial</option>
                    <option value="Warehouse">Warehouse / Godown</option>
                    <option value="Mixed">Mixed Use</option>
                  </Select>
                </div>
              </div>
            </div>
          )}

          {currentStep === 4 && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold text-gray-900">Review Your Information</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                <div>
                  <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
                    Business
                  </h3>
                  <dl className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <dt className="text-gray-600">Company</dt>
                      <dd className="font-medium text-gray-900">{formData.company_name || '—'}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-600">Type</dt>
                      <dd className="font-medium text-gray-900">{formData.business_type || '—'}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-600">Industry</dt>
                      <dd className="font-medium text-gray-900">{formData.industry || '—'}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-600">Sector</dt>
                      <dd className="font-medium text-gray-900">{formData.sector || '—'}</dd>
                    </div>
                  </dl>
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
                    Project
                  </h3>
                  <dl className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <dt className="text-gray-600">Project</dt>
                      <dd className="font-medium text-gray-900">{formData.project_name || '—'}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-600">Type</dt>
                      <dd className="font-medium text-gray-900">{formData.is_new ? 'New' : 'Expansion'}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-600">Stage</dt>
                      <dd className="font-medium text-gray-900">{formData.project_stage || '—'}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-600">Investment</dt>
                      <dd className="font-medium text-gray-900">
                        ₹{formData.investment_amount > 0 ? formData.investment_amount.toLocaleString() : '—'}
                      </dd>
                    </div>
                  </dl>
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
                    Location
                  </h3>
                  <dl className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <dt className="text-gray-600">District</dt>
                      <dd className="font-medium text-gray-900">
                        {formData.location_district ? `${formData.location_district}, ${formData.location_state}` : '—'}
                      </dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-600">City</dt>
                      <dd className="font-medium text-gray-900">{formData.location_city || '—'}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-600">Land</dt>
                      <dd className="font-medium text-gray-900">{formData.land_type || '—'}</dd>
                    </div>
                  </dl>
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
                    Operations
                  </h3>
                  <dl className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <dt className="text-gray-600">Employees</dt>
                      <dd className="font-medium text-gray-900">{formData.employees || 0}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-600">Pollution</dt>
                      <dd className="font-medium text-gray-900 capitalize">{formData.pollution_potential}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-600">Hazardous</dt>
                      <dd className="font-medium text-gray-900">{formData.hazardous_materials ? 'Yes' : 'No'}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-600">Boiler</dt>
                      <dd className="font-medium text-gray-900">{formData.has_boiler ? 'Yes' : 'No'}</dd>
                    </div>
                  </dl>
                </div>
              </div>

              <div className="p-4 bg-blue-50 border-l-4 border-blue-600 rounded-lg">
                <p className="text-sm text-blue-800">
                  <span className="font-semibold">Next:</span> After submission, the system will analyze
                  your project and provide a personalized approval roadmap.
                </p>
              </div>
            </div>
          )}

          <div className="flex flex-col-reverse sm:flex-row sm:justify-between gap-3 sm:items-center mt-8 pt-6 border-t">
            <Button variant="outline" onClick={handlePrev} disabled={currentStep === 0} className="w-full sm:w-auto">
              Previous
            </Button>
            <div className="flex w-full sm:w-auto gap-3">
              {currentStep < 4 && (
                <Button onClick={handleNext} disabled={loading} className="flex-1 sm:flex-none">
                  Next
                </Button>
              )}
              {currentStep === 4 && (
                <Button onClick={handleSubmit} disabled={loading} className="flex-1 sm:flex-none">
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    'Analyze Project'
                  )}
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}