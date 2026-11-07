import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '../api/client'
import type { components } from '../api/schema'

export type MissionOut = components['schemas']['MissionOut']
export type MissionSummary = components['schemas']['MissionSummary']
export type Step = 'diagnostic' | 'solutions' | 'regulation'

export function useMissions() {
  return useQuery({
    queryKey: ['missions'],
    queryFn: async () => {
      const { data, error } = await api.GET('/missions')
      if (error || !data) throw new Error('missions')
      return data
    },
  })
}

export function useMission(id: string) {
  return useQuery({
    queryKey: ['mission', id],
    queryFn: async () => {
      const { data, error } = await api.GET('/missions/{mission_id}', { params: { path: { mission_id: id } } })
      if (error || !data) throw new Error('mission')
      return data
    },
  })
}

export function useAnalyze(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (step: Step) => {
      const { data, error, response } = await api.POST('/missions/{mission_id}/analyze/{step}', {
        params: { path: { mission_id: id, step } },
      })
      if (error || !data) {
        const detail = (error as { detail?: unknown } | undefined)?.detail
        throw new Error(typeof detail === 'string' ? detail : `Erreur ${response.status}`)
      }
      return data
    },
    onSuccess: (data) => {
      qc.setQueryData(['mission', id], data)
      void qc.invalidateQueries({ queryKey: ['missions'] })
    },
  })
}
