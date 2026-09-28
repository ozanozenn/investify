import { CalendarView } from "@/components/calendar-view";
import { Disclaimer } from "@/components/disclaimer";
import { NavBar } from "@/components/nav-bar";

export default function TakvimPage() {
  return (
    <div className="min-h-screen pb-16">
      <NavBar />

      <div className="mx-auto max-w-6xl px-4 pt-6">
        <div className="mb-6">
          <h1 className="text-lg font-semibold text-foreground">Takvim</h1>
          <p className="mt-1 text-sm text-muted">
            Yaklaşan TCMB faiz kararları ve şirketlerin temettü/sermaye artırımı/halka arz duyuruları.
          </p>
        </div>

        <CalendarView />

        <div className="mt-8">
          <Disclaimer />
        </div>
      </div>
    </div>
  );
}
