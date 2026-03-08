import { useParams, Link } from 'react-router-dom'
import { useApi } from '@hooks/useApi'
import { fightersService } from '@services/fightersService'
import { fightsService } from '@services/fightsService'
import { LoadingSkeleton, DataCaveatNote, Card } from '@components/common'
import { FighterProfileHeader, FightRow } from '@components/features'

export default function FighterDetailPage() {
  const { id } = useParams<{ id: string }>()

  const { data: fighter, loading: fighterLoading, error: fighterError } = useApi(
    () => fightersService.getById(id!),
    [id],
  )

  const { data: fights, loading: fightsLoading } = useApi(
    () => fightsService.getList({ fighter_id: id, page_size: 50 }),
    [id],
  )

  const loading = fighterLoading || fightsLoading

  return (
    <div>
      <Link
        to="/fighters"
        className="inline-flex items-center gap-1 text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] transition-colors mb-6"
      >
        ← Fighter Lookup
      </Link>

      {fighterError && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-6 text-center text-sm text-red-600 dark:text-red-400">
          {fighterError}
        </div>
      )}

      {loading && (
        <div className="space-y-6">
          <LoadingSkeleton lines={3} />
          <div className="rounded-lg border border-[var(--color-border)] p-5">
            <LoadingSkeleton lines={2} />
          </div>
          <div className="rounded-lg border border-[var(--color-border)] p-5">
            <LoadingSkeleton lines={6} />
          </div>
        </div>
      )}

      {fighter && !fighterLoading && (
        <div className="space-y-6">
          <FighterProfileHeader fighter={fighter} />

          <DataCaveatNote>
            Detailed round-by-round stats are available for fights from 2015 onwards.
            Earlier fights may show results only.
          </DataCaveatNote>

          <Card
            header={
              <div className="flex items-center justify-between">
                <h2 className="font-semibold text-sm uppercase tracking-wide">Fight History</h2>
                {fights && (
                  <span className="text-xs text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
                    {fights.meta.total} fights
                  </span>
                )}
              </div>
            }
          >
            {fightsLoading && <LoadingSkeleton lines={5} />}

            {!fightsLoading && (!fights || fights.data.length === 0) && (
              <p className="py-4 text-center text-sm text-[var(--color-text-secondary-light)] dark:text-[var(--color-text-secondary)]">
                No fight history available.
              </p>
            )}

            {fights && !fightsLoading && fights.data.length > 0 && (
              <div className="-my-1">
                {fights.data.map((fight) => (
                  <FightRow key={fight.id} fight={fight} viewingFighterId={id} />
                ))}
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  )
}
