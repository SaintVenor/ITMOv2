import { ActionIcon, Button, useMantineColorScheme } from '@mantine/core';
import { Link, NavLink, useLocation } from 'react-router-dom';

export function Header({ onAdd }: { onAdd?: () => void }) {
  const location = useLocation();
  const { colorScheme, toggleColorScheme } = useMantineColorScheme();
  const dark = colorScheme === 'dark';
  const calendarHref = location.pathname === '/calendar'
    ? '/calendar' + location.search
    : (location.state?.calendarHref as string | undefined) ?? '/calendar';

  return <header className="header">
    <div className="shell header-inner">
      <Link className="brand" to={calendarHref}><span className="brand-mark" aria-hidden="true" /> Орбита</Link>
      <nav aria-label="Разделы">
        <NavLink to={calendarHref}>Календарь</NavLink>
        <NavLink to="/plans" state={{ calendarHref }}>Планы</NavLink>
      </nav>
      <div className="header-actions">
        <ActionIcon variant="transparent" size="lg" className="theme-toggle"
          aria-label={dark ? 'Светлая тема' : 'Тёмная тема'} title={dark ? 'Светлая тема' : 'Тёмная тема'}
          onClick={() => toggleColorScheme()}>{dark ? '☀' : '☾'}</ActionIcon>
        {onAdd && <Button className="header-add" onClick={onAdd}>＋ Добавить запись</Button>}
      </div>
    </div>
  </header>;
}
