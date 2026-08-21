import React, {
  useEffect,
  useState
} from 'react';

import {
  Box,
  Text,
  render,
  useApp,
  useInput
} from 'ink';

import {
  spawn
} from 'node:child_process';

import {
  fileURLToPath
} from 'node:url';

import {
  dirname,
  resolve
} from 'node:path';

const h = React.createElement;

const BLUE = '#2f81f7';
const MUTED = '#7d8590';
const DIM = '#484f58';

const HERE = dirname(
  fileURLToPath(import.meta.url)
);

const ROOT = resolve(
  HERE,
  '..',
  '..'
);

const PYTHON = resolve(
  ROOT,
  '.venv',
  'bin',
  'python'
);

function friendlyDate(value) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return 'Unknown time';
  }

  return date.toLocaleString(
    undefined,
    {
      dateStyle: 'medium',
      timeStyle: 'short'
    }
  );
}

function bridge(command, payload = {}) {
  return new Promise(
    (resolvePromise, reject) => {
      const child = spawn(
        PYTHON,
        [
          '-m',
          'app.tui_bridge',
          command
        ],
        {
          cwd: ROOT,
          env: process.env,
          stdio: [
            'pipe',
            'pipe',
            'pipe'
          ]
        }
      );

      let stdout = '';
      let stderr = '';

      child.stdout.on(
        'data',
        chunk => {
          stdout += chunk.toString();
        }
      );

      child.stderr.on(
        'data',
        chunk => {
          stderr += chunk.toString();
        }
      );

      child.on(
        'error',
        reject
      );

      child.on(
        'close',
        code => {
          try {
            const data = JSON.parse(
              stdout.trim() || '{}'
            );

            if (
              code !== 0
              || data.ok === false
            ) {
              reject(
                new Error(
                  data.error
                  || stderr.trim()
                  || 'Action failed.'
                )
              );

              return;
            }

            resolvePromise(data);

          } catch {
            reject(
              new Error(
                stderr.trim()
                || 'Unreadable response.'
              )
            );
          }
        }
      );

      child.stdin.end(
        JSON.stringify(payload)
      );
    }
  );
}

function copyToClipboard(value) {
  const commands =
    process.platform === 'darwin'
      ? [['pbcopy', []]]
      : process.platform === 'win32'
        ? [['clip', []]]
        : [
            ['wl-copy', []],
            ['xclip', ['-selection', 'clipboard']]
          ];

  return new Promise(
    (resolvePromise, reject) => {
      const attempt = index => {
        const command = commands[index];

        if (!command) {
          reject(new Error('No supported clipboard command was found.'));
          return;
        }

        const child = spawn(
          command[0],
          command[1],
          {
            stdio: ['pipe', 'ignore', 'ignore']
          }
        );

        let failed = false;

        child.on(
          'error',
          () => {
            failed = true;
            attempt(index + 1);
          }
        );
        child.on(
          'close',
          code => {
            if (failed) {
              return;
            }

            if (code === 0) {
              resolvePromise();
            } else {
              attempt(index + 1);
            }
          }
        );
        child.stdin.on('error', () => {});
        child.stdin.end(value);
      };

      attempt(0);
    }
  );
}

function Header({crumb = []}) {
  return h(
    Box,
    {
      flexDirection: 'column',
      marginBottom: 1
    },
    h(
      Text,
      {
        color: BLUE,
        bold: true
      },
      '◆ JunctionNow Discord Bot Manager'
    ),
    crumb.length
      ? h(
          Text,
          {
            color: MUTED
          },
          [
            'JunctionNow',
            ...crumb
          ].join('  ›  ')
        )
      : null
  );
}

function Footer({root = false}) {
  return h(
    Box,
    {
      marginTop: 1
    },
    h(
      Text,
      {
        color: DIM
      },
      root
        ? '↑↓ move   enter select   esc exit'
        : '↑↓ move   enter select   ← back   esc back'
    )
  );
}

function Message({
  title,
  message,
  back
}) {
  useInput(
    (input, key) => {
      if (
        key.escape
        || key.return
      ) {
        back();
      }
    }
  );

  return h(
    Box,
    {
      flexDirection: 'column'
    },
    h(Header),
    h(
      Text,
      {
        bold: true,
        color: BLUE
      },
      title
    ),
    h(
      Box,
      {
        marginTop: 1
      },
      h(
        Text,
        null,
        message
      )
    ),
    h(
      Box,
      {
        marginTop: 1
      },
      h(
        Text,
        {
          color: DIM
        },
        'enter or esc back'
      )
    )
  );
}

function Menu({
  title,
  subtitle,
  items,
  select,
  back,
  root = false
}) {
  const [index, setIndex] = useState(0);
  const {exit} = useApp();

  useEffect(
    () => {
      if (
        index >= items.length
      ) {
        setIndex(
          Math.max(
            0,
            items.length - 1
          )
        );
      }
    },
    [
      index,
      items.length
    ]
  );

  useInput(
    (input, key) => {
      if (
        key.upArrow
        || input === 'k'
      ) {
        if (items.length) {
          setIndex(
            value => (
              value - 1 + items.length
            ) % items.length
          );
        }

        return;
      }

      if (
        key.downArrow
        || input === 'j'
      ) {
        if (items.length) {
          setIndex(
            value => (
              value + 1
            ) % items.length
          );
        }

        return;
      }

      if (
        key.return
        || key.rightArrow
      ) {
        if (items[index] && !items[index].disabled) {
          select(
            items[index]
          );
        }

        return;
      }

      if (key.escape) {
        if (root) {
          exit();
        } else if (back) {
          back();
        }

        return;
      }

      if (key.leftArrow && back) {
        back();
      }
    }
  );

  return h(
    Box,
    {
      flexDirection: 'column'
    },
    h(Header),
    title
      ? h(
          Text,
          {
            bold: true
          },
          title
        )
      : null,
    subtitle
      ? h(
          Text,
          {
            color: MUTED
          },
          subtitle
        )
      : null,
    h(
      Box,
      {
        flexDirection: 'column',
        marginTop: 1
      },
      ...items.map(
        (item, itemIndex) => {
          const selected =
            itemIndex === index;

          return h(
            Box,
            {
              flexDirection: 'column',
              key:
                `${item.id}-${itemIndex}`
            },
            h(
              Box,
              {},
              h(Text, {color: selected ? BLUE : DIM}, selected ? '› ' : '  '),
              item.status
                ? h(Text, {color: item.statusColor || MUTED}, `${item.status} `)
                : null,
              h(
                Text,
                {
                  bold: selected,
                  color: item.disabled ? DIM : selected ? BLUE : undefined
                },
                item.label
              )
            ),
            item.description
              ? h(Box, {marginLeft: 4}, h(Text, {color: MUTED}, item.description))
              : null
          );
        }
      )
    ),
    h(
      Footer,
      {
        root
      }
    )
  );
}

function MultiSelect({
  title,
  subtitle,
  items,
  submit,
  back
}) {
  const [index, setIndex] = useState(0);
  const [selected, setSelected] = useState(new Set());

  useInput(
    (input, key) => {
      if ((key.upArrow || input === 'k') && items.length) {
        setIndex(value => (value - 1 + items.length) % items.length);
        return;
      }

      if ((key.downArrow || input === 'j') && items.length) {
        setIndex(value => (value + 1) % items.length);
        return;
      }

      if (input === ' ' && items[index]) {
        setSelected(
          current => {
            const next = new Set(current);
            const id = items[index].id;

            if (next.has(id)) {
              next.delete(id);
            } else {
              next.add(id);
            }

            return next;
          }
        );
        return;
      }

      if (key.return && selected.size) {
        submit(items.filter(item => selected.has(item.id)));
        return;
      }

      if (key.escape) {
        back();
      }
    }
  );

  return h(
    Box,
    {flexDirection: 'column'},
    h(Header),
    h(Text, {bold: true}, title),
    h(Text, {color: MUTED}, subtitle),
    h(
      Box,
      {flexDirection: 'column', marginTop: 1},
      ...(
        items.length
          ? items.map(
              (item, itemIndex) => h(
                Text,
                {
                  key: item.id,
                  color: itemIndex === index ? BLUE : undefined
                },
                `${itemIndex === index ? '›' : ' '} `
                + `[${selected.has(item.id) ? 'x' : ' '}] ${item.label}`
              )
            )
          : [h(Text, {key: 'empty', color: MUTED}, 'No matching articles')]
      )
    ),
    h(
      Box,
      {marginTop: 1},
      h(Text, {color: DIM}, 'space select   enter submit   esc back')
    )
  );
}

function LineInput({
  title,
  help,
  initial = '',
  secret = false,
  submit,
  back
}) {
  const [value, setValue] = useState(
    initial
  );

  useInput(
    (input, key) => {
      if (key.escape) {
        back();
        return;
      }

      if (key.return) {
        submit(value);
        return;
      }

      if (
        key.backspace
        || key.delete
      ) {
        setValue(
          current =>
            current.slice(
              0,
              -1
            )
        );

        return;
      }

      if (
        input
        && !key.ctrl
        && !key.meta
        && input !== '\r'
        && input !== '\n'
      ) {
        setValue(
          current =>
            current + input
        );
      }
    }
  );

  return h(
    Box,
    {
      flexDirection: 'column'
    },
    h(Header),
    h(
      Text,
      {
        bold: true
      },
      title
    ),
    help
      ? h(
          Text,
          {
            color: MUTED
          },
          help
        )
      : null,
    h(
      Box,
      {
        marginTop: 1
      },
      h(
        Text,
        {
          color: BLUE
        },
        '◆ '
      ),
      h(
        Text,
        null,
        secret
          ? '•'.repeat(
              value.length
            )
          : value
      ),
      h(
        Text,
        {
          color: MUTED
        },
        '█'
      )
    ),
    h(
      Box,
      {
        marginTop: 1
      },
      h(
        Text,
        {
          color: DIM
        },
        'enter save   esc cancel'
      )
    )
  );
}

function Confirm({
  title,
  message,
  confirm,
  back
}) {
  useInput(
    (input, key) => {
      if (
        input.toLowerCase()
        === 'y'
      ) {
        confirm();
        return;
      }

      if (
        key.escape
        || input.toLowerCase()
        === 'n'
      ) {
        back();
      }
    }
  );

  return h(
    Box,
    {
      flexDirection: 'column'
    },
    h(Header),
    h(
      Text,
      {
        bold: true,
        color: 'yellow'
      },
      title
    ),
    h(
      Box,
      {
        marginTop: 1
      },
      h(
        Text,
        null,
        message
      )
    ),
    h(
      Box,
      {
        marginTop: 1
      },
      h(
        Text,
        {
          color: DIM
        },
        'y confirm   n/esc cancel'
      )
    )
  );
}

function Loading() {
  return h(
    Box,
    null,
    h(
      Text,
      {
        color: BLUE
      },
      '◆ Loading…'
    )
  );
}

function Root({
  go
}) {
  return h(
    Menu,
    {
      root: true,
      title: 'Discord Bot Manager',
      subtitle:
        'Local control for JunctionNow.',
      items: [
        {
          id: 'overview',
          label: 'Overview'
        },
        {
          id: 'servers',
          label: 'Servers'
        },
        {
          id: 'features',
          label: 'Features'
        },
        {
          id: 'manage-bot',
          label: 'Manage Bot'
        },
        {
          id: 'storage',
          label: 'Storage'
        },
        {
          id: 'settings',
          label: 'Settings'
        }
      ],
      select:
        item => go({
          name: item.id
        })
    }
  );
}

function Dashboard({
  back
}) {
  const [data, setData] =
    useState(null);

  const [error, setError] =
    useState(null);

  useEffect(
    () => {
      bridge('overview')
        .then(setData)
        .catch(setError);
    },
    []
  );

  useInput(
    (input, key) => {
      if (
        key.escape
        || key.leftArrow
      ) {
        back();
      }
    }
  );

  if (error) {
    return h(
      Message,
      {
        title: 'Overview error',
        message: error.message,
        back
      }
    );
  }

  if (!data) {
    return h(Loading);
  }

  const daemon =
    data.daemon?.running
      ? 'Running'
      : 'Stopped';

  const rows = [
    ['Daemon', daemon],
    [
      'Feed',
      data.feed_enabled
        ? 'Running'
        : 'Paused'
    ],
    [
      'Servers',
      data.servers
    ],
    [
      'Configured',
      data.configured
    ],
    [
      'Banned',
      data.banned
    ],
    [
      'Posts',
      data.posts
    ],
    [
      'Deliveries',
      data.deliveries
    ],
    [
      'Photo requests',
      data.photo_requests
    ]
  ];

  return h(
    Box,
    {
      flexDirection: 'column'
    },
    h(Header),
    h(
      Text,
      {
        bold: true
      },
      'Overview'
    ),
    h(
      Box,
      {
        flexDirection: 'column',
        marginTop: 1
      },
      ...rows.map(
        ([label, value]) =>
          h(
            Box,
            {
              key: label
            },
            h(
              Text,
              {
                color: MUTED
              },
              `${label.padEnd(18)}`
            ),
            h(
              Text,
              {
                color:
                  label === 'Daemon'
                  && value === 'Stopped'
                    ? 'red'
                    : undefined
              },
              String(value)
            )
          )
      )
    ),
    h(Footer)
  );
}

function ManageBot({
  go,
  back
}) {
  return h(
    Menu,
    {
      title: 'Manage Bot',
      subtitle: 'Internal bot management.',
      back,
      items: [
        {id: 'configuration', label: 'Configuration'},
        {id: 'activity', label: 'Logs'},
        {id: 'overview', label: 'Analytics'},
        {id: 'invite-copy', label: 'Copy invite link'},
        {id: 'invite-show', label: 'Invite bot or restore permissions'}
      ],
      select: item => go({name: item.id})
    }
  );
}

function Configuration({
  go,
  back
}) {
  const [data, setData] = useState(null);

  useEffect(
    () => {
      bridge('config-status').then(setData);
    },
    []
  );

  if (!data) {
    return h(Loading);
  }

  return h(
    Menu,
    {
      title: 'Configuration',
      subtitle: 'Private bot and internal server settings.',
      back,
      items: [
        {id: 'setup', label: 'Credentials'},
        {
          id: 'photo-setup',
          label:
            data.photo_destination_configured
              ? 'Management Server: configured'
              : 'Management Server: not configured'
        }
      ],
      select:
        item => go(
          item.id === 'photo-setup'
            ? {name: 'photo-setup', config: data}
            : {name: item.id}
        )
    }
  );
}

function Features({
  go,
  back
}) {
  return h(
    Menu,
    {
      title: 'Features',
      subtitle: 'Features provided by the JunctionNow bot.',
      back,
      items: [
        {id: 'posts', label: 'Posts'},
        {id: 'broadcast', label: 'Broadcast'},
        {id: 'feature-settings', label: 'Settings'}
      ],
      select: item => go({name: item.id})
    }
  );
}

function FeatureSettings({
  go,
  back
}) {
  return h(
    Menu,
    {
      title: 'Feature Settings',
      subtitle: 'How bot features run.',
      back,
      items: [
        {id: 'schedule', label: 'Post Schedule'}
      ],
      select: item => go({name: item.id})
    }
  );
}

function Retention({
  go,
  back
}) {
  const [data, setData] = useState(null);

  useEffect(
    () => {
      bridge('config-status').then(setData);
    },
    []
  );

  if (!data) {
    return h(Loading);
  }

  return h(
    Menu,
    {
      title: 'Data Retention',
      subtitle: 'Limits keep active JSON state bounded.',
      back,
      items: [
        {id: 'max_posts', label: `Posts: ${data.state_max_posts}`},
        {id: 'max_events', label: `Activity events: ${data.state_max_events}`},
        {id: 'backup_count', label: `Backups: ${data.state_backup_count}`}
      ],
      select:
        item => go({
          name: 'retention-choice',
          field: item.id,
          config: data
        })
    }
  );
}

function RetentionChoice({
  screen,
  go,
  back
}) {
  const choices = {
    max_posts: [250, 500, 1000, 2000, 5000],
    max_events: [100, 250, 500, 1000, 2000],
    backup_count: [1, 3, 5, 10, 20]
  };
  const labels = {
    max_posts: 'Retained Posts',
    max_events: 'Retained Activity Events',
    backup_count: 'State Backups'
  };
  const current = {
    max_posts: screen.config.state_max_posts,
    max_events: screen.config.state_max_events,
    backup_count: screen.config.state_backup_count
  };

  return h(
    Menu,
    {
      title: labels[screen.field],
      subtitle: 'Choose a bounded local limit.',
      back,
      items: choices[screen.field].map(
        value => ({
          id: String(value),
          label: String(value),
          status: value === current[screen.field] ? '●' : undefined,
          statusColor: 'green',
          value
        })
      ),
      select:
        async item => {
          const values = {...current, [screen.field]: item.value};

          try {
            await bridge('retention-set', values);
            go({
              name: 'message',
              title: 'Data Retention',
              message: `${labels[screen.field]} set to ${item.value}.`
            });
          } catch (error) {
            go({name: 'message', title: 'Retention failed', message: error.message});
          }
        }
    }
  );
}

function Settings({
  go,
  back
}) {
  return h(
    Menu,
    {
      title: 'Settings',
      subtitle: 'Runtime and Bot Manager settings.',
      back,
      items: [
        {id: 'start', label: 'Start bot'},
        {id: 'stop', label: 'Stop bot'},
        {id: 'updates', label: 'Updates'},
        {id: 'manager-uninstall', label: 'Uninstall Bot Manager'}
      ],
      select: item => go(
        item.id === 'start' || item.id === 'stop'
          ? {name: 'bot-action', action: item.id}
          : {name: item.id}
      )
    }
  );
}

function Storage({
  go,
  back
}) {
  return h(
    Menu,
    {
      title: 'Storage',
      subtitle: 'Where bot data lives and how it is kept.',
      back,
      items: [
        {id: 'storage-features', label: 'Features'},
        {id: 'storage-settings', label: 'Destinations'},
        {id: 'storage-maintenance', label: 'Maintenance'},
        {id: 'storage-preferences', label: 'Preferences'}
      ],
      select: item => go({name: item.id})
    }
  );
}

function StorageFeatures({back}) {
  const [data, setData] = useState(null);

  useEffect(() => {
    bridge('storage-status').then(setData);
  }, []);

  if (!data) {
    return h(Loading);
  }

  const features = data.features;

  return h(Menu, {
    title: 'Storage Features',
    subtitle: 'Features using retained local data.',
    back,
    items: [
      {id: 'posts', label: 'Posts', description: `${features.posts} posts · ${features.deliveries} deliveries · limit ${data.limits.posts}`, disabled: true},
      {id: 'photos', label: 'Request Photos', description: `${features.photo_requests} active requests · ${features.photo_submissions} submissions`, disabled: true},
      {id: 'broadcasts', label: 'Broadcast', description: `${features.broadcasts} retained`, disabled: true},
      {id: 'activity', label: 'Activity', description: `${features.activity} events · limit ${data.limits.activity}`, disabled: true}
    ],
    select: () => {}
  });
}

function StorageSettings({go, back}) {
  const [data, setData] = useState(null);

  useEffect(() => {
    bridge('storage-status').then(setData);
  }, []);

  if (!data) {
    return h(Loading);
  }

  const backend = (id, label) => {
    const item = data.backends[id];
    const active = item.status === 'active';
    const problem = item.status === 'inactive';

    return {
      id,
      label,
      status: active || problem ? '●' : '○',
      statusColor: active ? 'green' : problem ? 'red' : MUTED,
      description: item.label,
      disabled: !active
    };
  };

  return h(Menu, {
    title: 'Storage Destinations',
    subtitle: 'Places where bot data can be stored.',
    back,
    items: [
      backend('json', 'Default · JSON'),
      backend('mysql', 'MySQL'),
      backend('postgresql', 'PostgreSQL')
    ],
    select: item => go(item.id === 'json' ? {name: 'storage-info'} : {name: item.id})
  });
}

function StorageMaintenance({go, back}) {
  return h(Menu, {
    title: 'Storage Maintenance',
    subtitle: 'Safe, focused actions for local data.',
    back,
    items: [
      {id: 'storage-clean', label: 'Clean Safe Data', description: 'Remove finished actions and withdrawn broadcasts.'},
      {id: 'storage-dump', label: 'Dump Snapshot', description: 'Save a private JSON copy on this machine.'},
      {id: 'storage-clear', label: 'Clear All', description: 'Unavailable while delivery tracking is active.', disabled: true}
    ],
    select: item => go({name: item.id})
  });
}

function StoragePreferences({go, back}) {
  return h(Menu, {
    title: 'Storage Preferences',
    subtitle: 'Local retention and archive settings.',
    back,
    items: [
      {id: 'retention', label: 'Data Retention'},
      {id: 'storage-archive', label: 'Archive Location', description: 'data/backups'}
    ],
    select: item => go({name: item.id})
  });
}

function Schedule({
  go,
  back
}) {
  const [data, setData] = useState(null);

  useEffect(
    () => {
      bridge('config-status').then(setData);
    },
    []
  );

  if (!data) {
    return h(Loading);
  }

  const choices = [30, 60, 120, 360, 720, 1440];

  return h(
    Menu,
    {
      title: 'Schedule',
      subtitle:
        `Detected timezone: ${data.timezone} · Current: ${data.sync_interval_minutes} minutes`,
      back,
      items: choices.map(
        minutes => ({
          id: String(minutes),
          label:
            minutes < 60
              ? `${minutes} minutes`
              : `${minutes / 60} hour${minutes === 60 ? '' : 's'}`,
          status: minutes === data.sync_interval_minutes ? '●' : undefined,
          statusColor: 'green',
          minutes
        })
      ),
      select:
        async item => {
          try {
            await bridge('schedule-set', {minutes: item.minutes});
            go({
              name: 'message',
              title: 'Schedule',
              message: `Post checks now run every ${item.minutes} minutes.`
            });
          } catch (error) {
            go({name: 'message', title: 'Schedule failed', message: error.message});
          }
        }
    }
  );
}

function Invite({
  copy,
  back
}) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(
    () => {
      bridge('invite-link')
        .then(
          async result => {
            if (copy) {
              await copyToClipboard(result.url);
            }

            setData(result);
          }
        )
        .catch(setError);
    },
    [copy]
  );

  if (error) {
    return h(Message, {title: 'Invite link', message: error.message, back});
  }

  if (!data) {
    return h(Loading);
  }

  return h(
    Message,
    {
      title: copy ? 'Invite link copied' : 'Invite link',
      message:
        copy
          ? 'The invite link is ready to paste.'
          : `${data.url}\n\nRequired: ${data.permissions.join(', ')}`,
      back
    }
  );
}

function Setup({
  go,
  back
}) {
  const [data, setData] =
    useState(null);

  useEffect(
    () => {
      bridge('config-status')
        .then(setData);
    },
    []
  );

  if (!data) {
    return h(Loading);
  }

  return h(
    Menu,
    {
      title: 'Setup',
      subtitle: 'Private local settings.',
      back,
      items: [
        {
          id: 'token',
          label:
            data.token_configured
              ? 'Discord token: configured'
              : 'Discord token: required'
        },
        {
          id: 'application',
          label:
            data.application_id
              ? `Application ID: ${data.application_id}`
              : 'Application ID: required'
        }
      ],
      select:
        item => go({
          name: 'setup-value',
          setting: item.id,
          config: data
        })
    }
  );
}

function PhotoSetup({
  screen,
  go,
  back
}) {
  const data = screen.config;

  return h(
    Menu,
    {
      title: 'Photo destination',
      subtitle:
        'Use a server and channel together, or use a webhook.',
      back,
      items: [
        {
          id: 'photo-server',
          label:
            data.photo_guild_id
              ? `Server ID: ${data.photo_guild_id}`
              : 'Server ID: not configured'
        },
        {
          id: 'photo-channel',
          label:
            data.photo_channel_id
              ? `Channel ID: ${data.photo_channel_id}`
              : 'Channel ID: not configured'
        },
        {
          id: 'photo-webhook',
          label:
            data.photo_webhook_configured
              ? 'Webhook: configured'
              : 'Webhook: not configured'
        },
        {
          id: 'photo-clear',
          label: 'Disable photo destination'
        }
      ],
      select:
        item => go({
          name:
            item.id === 'photo-clear'
              ? 'photo-clear'
              : 'setup-value',
          setting: item.id
        })
    }
  );
}

function Servers({
  go,
  back
}) {
  const [data, setData] =
    useState(null);

  useEffect(
    () => {
      bridge('servers')
        .then(setData);
    },
    []
  );

  if (!data) {
    return h(Loading);
  }

  const items = data.items.map(
    server => ({
      id: server.id,
      label: server.name,
      status:
        server.banned
          ? '●'
          : server.enabled
            ? '●'
            : '○',
      statusColor:
        server.banned
          ? 'red'
          : server.enabled
            ? 'green'
            : MUTED,
      server
    })
  );

  return h(
    Menu,
    {
      title: 'Servers',
      subtitle:
        'Installed and known servers.',
      items,
      back,
      select:
        item => go({
          name: 'server',
          server: item.server
        })
    }
  );
}

function Server({
  screen,
  go,
  back
}) {
  const server =
    screen.server;

  return h(
    Menu,
    {
      title: server.name,
      subtitle:
        `ID ${server.id}`,
      back,
      items: [
        {
          id: 'channel',
          label:
            server.channel_id
              ? `Posting channel: ${server.channel_id}`
              : 'Set posting channel'
        },
        {
          id:
            server.banned
              ? 'unban'
              : 'ban',
          label:
            server.banned
              ? 'Unban server'
              : 'Ban server'
        },
        {
          id: 'delete',
          label: 'Delete local server data'
        }
      ],
      select: item => {
        if (
          item.id === 'channel'
        ) {
          go({
            name: 'set-channel',
            server
          });

          return;
        }

        if (
          item.id === 'ban'
          || item.id === 'unban'
        ) {
          go({
            name: 'server-ban',
            server,
            action:
              item.id
          });

          return;
        }

        go({
          name: 'server-delete',
          server
        });
      }
    }
  );
}

function Posts({
  go,
  back
}) {
  const [data, setData] =
    useState(null);

  useEffect(
    () => {
      bridge('posts')
        .then(setData);
    },
    []
  );

  if (!data) {
    return h(Loading);
  }

  return h(
    Menu,
    {
      title: 'Posts',
      subtitle:
        'Latest tracked posts.',
      back,
      items:
        [
          {
            id: 'update-all',
            label: 'Update all posts now',
            status: '↻',
            statusColor: BLUE
          },
          {
            id: 'toggle-updates',
            label:
              data.feed_enabled
                ? 'Pause automatic post updates'
                : 'Resume automatic post updates',
            status:
              data.feed_enabled
                ? '●'
                : '○',
            statusColor:
              data.feed_enabled
                ? 'green'
                : MUTED
          },
          {
            id: 'addons',
            label: 'Add-ons'
          },
          ...data.items.map(
            post => ({
              id: post.post_id,
              label:
                post.title
                || 'JunctionNow',
              status:
                post.withdrawn
                  ? '×'
                  : post.photo_requested
                    ? '●'
                    : '○',
              statusColor:
                post.withdrawn
                  ? 'red'
                  : post.photo_requested
                    ? BLUE
                    : DIM,
              post
            })
          )
        ],
      select: item => {
        if (item.id === 'update-all') {
          bridge(
            'queue',
            {
              action: 'sync_now'
            }
          ).then(
            () => go({
              name: 'message',
              title: 'Posts',
              message:
                'Post update started. '
                + 'New and changed posts will be delivered.'
            })
          ).catch(
            error => go({
              name: 'message',
              title: 'Update failed',
              message: error.message
            })
          );

          return;
        }

        if (item.id === 'toggle-updates') {
          bridge(
            'queue',
            {
              action: 'feed',
              payload: {
                enabled:
                  !data.feed_enabled
              }
            }
          ).then(
            () => go({
              name: 'message',
              title: 'Posts',
              message:
                data.feed_enabled
                  ? 'Automatic post updates paused.'
                  : 'Automatic post updates resumed.'
            })
          ).catch(
            error => go({
              name: 'message',
              title: 'Update failed',
              message: error.message
            })
          );

          return;
        }

        if (item.id === 'addons') {
          go({name: 'posts-addons'});
          return;
        }

        go({
          name: 'post',
          post: item.post
        });
      }
    }
  );
}

function Post({
  screen,
  go,
  back
}) {
  const post = screen.post;

  return h(
    Menu,
    {
      title:
        post.title
        || 'JunctionNow',
      subtitle:
        post.url || '',
      back,
      items: [
        {
          id:
            post.withdrawn
              ? 'restore'
              : 'withdraw',
          label:
            post.withdrawn
              ? 'Restore post'
              : 'Withdraw from all servers'
        },
        {
          id: 'delete',
          label: 'Delete stored post data'
        }
      ],
      select:
        item => go({
          name: 'post-action',
          action: item.id,
          post
        })
    }
  );
}

function PostsAddons({
  go,
  back
}) {
  const [data, setData] = useState(null);

  useEffect(
    () => {
      bridge('config-status').then(setData);
    },
    []
  );

  if (!data) {
    return h(Loading);
  }

  return h(
    Menu,
    {
      title: 'Add-ons',
      subtitle: 'Optional Posts features.',
      back,
      items: [
        {
          id: 'request-photos',
          label:
            data.photo_destination_configured
              ? 'Request Photos'
              : 'Request Photos · configure destination first',
          disabled: !data.photo_destination_configured
        },
        {
          id: 'stop-photos',
          label: 'Stop Requesting Photos',
          disabled: !data.photo_destination_configured
        },
        {
          id: 'photo-destination',
          label:
            data.photo_destination_configured
              ? 'Photo destination: configured'
              : 'Photo destination: not configured'
        }
      ],
      select:
        item => go(
          item.id === 'photo-destination'
            ? {name: 'photo-setup', config: data}
            : {
                name: 'photo-posts',
                enabled: item.id === 'request-photos'
              }
        )
    }
  );
}

function PhotoPosts({
  screen,
  go,
  back
}) {
  const [data, setData] = useState(null);

  useEffect(
    () => {
      bridge('posts').then(setData);
    },
    []
  );

  if (!data) {
    return h(Loading);
  }

  const posts = data.items.filter(
    post => Boolean(post.photo_requested) !== screen.enabled
  );

  return h(
    MultiSelect,
    {
      title:
        screen.enabled
          ? 'Request Photos'
          : 'Stop Requesting Photos',
      subtitle: 'Choose one or more articles.',
      back,
      items: posts.map(
        post => ({
          id: post.post_id,
          label: post.title || 'JunctionNow',
          post
        })
      ),
      submit:
        async items => {
          try {
            await bridge(
              'queue',
              {
                action: 'photo_requests',
                payload: {
                  post_ids: items.map(item => item.post.post_id),
                  enabled: screen.enabled
                }
              }
            );

            go({
              name: 'message',
              title: 'Posts',
              message:
                `${items.length} article${items.length === 1 ? '' : 's'} queued.`
            });
          } catch (error) {
            go({
              name: 'message',
              title: 'Action failed',
              message: error.message
            });
          }
        }
    }
  );
}

function Broadcasts({
  go,
  back
}) {
  const [data, setData] = useState(null);

  useEffect(
    () => {
      bridge('broadcasts').then(setData);
    },
    []
  );

  if (!data) {
    return h(Loading);
  }

  return h(
    Menu,
    {
      title: 'Broadcast',
      subtitle: 'Send or withdraw JunctionNow messages.',
      back,
      items: [
        {id: 'send', label: 'Send Broadcast'},
        ...data.items.map(
          item => ({
            id: item.id,
            label:
              `${item.withdrawn ? 'Withdrawn · ' : item.status === 'scheduled' ? 'Scheduled · ' : ''}`
              + `${item.message.slice(0, 60)} · `
              + friendlyDate(item.sent_at || item.created_at),
            disabled: Boolean(item.withdrawn),
            broadcast: item
          })
        )
      ],
      select:
        item => go(
          item.id === 'send'
            ? {name: 'broadcast-compose'}
            : {name: 'broadcast-withdraw', broadcast: item.broadcast}
        )
    }
  );
}

function Activity({
  back
}) {
  const [data, setData] =
    useState(null);

  useEffect(
    () => {
      bridge('activity')
        .then(setData);
    },
    []
  );

  if (!data) {
    return h(Loading);
  }

  return h(
    Menu,
    {
      title: 'Activity',
      subtitle:
        'Only saved operational events.',
      back,
      items:
        data.items.length
          ? data.items.map(
              (item, index) => ({
                id:
                  `${index}-${item.at}`,
                label:
                  `${item.type.replaceAll('_', ' ')} · `
                  + friendlyDate(item.at)
              })
            )
          : [
              {
                id: 'none',
                label: 'No activity'
              }
            ],
      select: () => {}
    }
  );
}

function Updates({
  go,
  back
}) {
  const [data, setData] =
    useState(null);

  const [error, setError] =
    useState(null);

  useEffect(
    () => {
      bridge('update-status')
        .then(setData)
        .catch(setError);
    },
    []
  );

  useInput(
    (input, key) => {
      if (
        key.escape
        || key.leftArrow
      ) {
        back();
      }

      if (
        key.return
        && data?.update_available
        && data?.fast_forward
      ) {
        go({
          name: 'update-confirm',
          update: data
        });
      }
    }
  );

  if (error) {
    return h(
      Message,
      {
        title: 'Update check failed',
        message: error.message,
        back
      }
    );
  }

  if (!data) {
    return h(Loading);
  }

  return h(
    Box,
    {
      flexDirection: 'column'
    },
    h(Header),
    h(Text, {bold: true}, 'Updates'),
    h(
      Box,
      {
        flexDirection: 'column',
        marginTop: 1
      },
      h(Text, {}, `Version           ${data.version}`),
      h(Text, {}, `Installed         ${data.installed_revision}`),
      h(Text, {}, `GitHub main       ${data.available_revision}`),
      h(
        Text,
        {
          color:
            data.update_available
              ? BLUE
              : 'green'
        },
        data.update_available
          ? data.fast_forward
            ? 'Update available · enter to review'
            : 'Update cannot be fast-forwarded safely'
          : 'Up to date'
      )
    ),
    h(Footer)
  );
}

function App() {
  const [stack, setStack] =
    useState([
      {
        name: 'root'
      }
    ]);

  const screen =
    stack[
      stack.length - 1
    ];

  const go = next =>
    setStack(
      current => [
        ...current,
        next
      ]
    );

  const back = () =>
    setStack(
      current =>
        current.length > 1
          ? current.slice(
              0,
              -1
            )
          : current
    );

  const done = message =>
    go({
      name: 'message',
      title: 'Done',
      message
    });

  if (
    screen.name
    === 'root'
  ) {
    return h(
      Root,
      {
        go
      }
    );
  }

  if (
    screen.name
    === 'overview'
  ) {
    return h(
      Dashboard,
      {
        back
      }
    );
  }

  if (
    screen.name
    === 'manage-bot'
  ) {
    return h(ManageBot, {go, back});
  }

  if (
    screen.name
    === 'configuration'
  ) {
    return h(Configuration, {go, back});
  }

  if (
    screen.name
    === 'features'
  ) {
    return h(Features, {go, back});
  }

  if (
    screen.name
    === 'feature-settings'
  ) {
    return h(FeatureSettings, {go, back});
  }

  if (
    screen.name
    === 'retention'
  ) {
    return h(Retention, {go, back});
  }

  if (
    screen.name
    === 'retention-choice'
  ) {
    return h(RetentionChoice, {screen, go, back});
  }

  if (
    screen.name
    === 'settings'
  ) {
    return h(Settings, {go, back});
  }

  if (
    screen.name
    === 'storage'
  ) {
    return h(Storage, {go, back});
  }

  if (screen.name === 'storage-features') {
    return h(StorageFeatures, {back});
  }

  if (screen.name === 'storage-settings') {
    return h(StorageSettings, {go, back});
  }

  if (screen.name === 'storage-maintenance') {
    return h(StorageMaintenance, {go, back});
  }

  if (screen.name === 'storage-preferences') {
    return h(StoragePreferences, {go, back});
  }

  if (
    screen.name
    === 'schedule'
  ) {
    return h(Schedule, {go, back});
  }

  if (
    screen.name
    === 'storage-info'
  ) {
    return h(
      Message,
      {
        title: 'JSON Storage',
        message:
          'Active state is stored in data/state.json with atomic writes, locking, and bounded backups.',
        back
      }
    );
  }

  if (screen.name === 'storage-archive') {
    return h(Message, {
      title: 'Archive Location',
      message: 'Bounded state backups are kept in data/backups on this machine.',
      back
    });
  }

  if (screen.name === 'storage-clean') {
    return h(Confirm, {
      title: 'Clean Safe Data',
      message: 'Remove finished actions and withdrawn broadcasts? Delivery tracking stays safe.',
      back,
      confirm: async () => {
        const result = await bridge('storage-clean');
        done(`Removed ${result.removed.actions} finished actions and ${result.removed.broadcasts} withdrawn broadcasts.`);
      }
    });
  }

  if (screen.name === 'storage-dump') {
    return h(Confirm, {
      title: 'Dump Snapshot',
      message: 'Save a private JSON copy of current bot data on this machine?',
      back,
      confirm: async () => {
        const result = await bridge('storage-dump');
        done(`Snapshot saved to ${result.location}.`);
      }
    });
  }

  if (
    screen.name
    === 'invite-copy'
    || screen.name === 'invite-show'
  ) {
    return h(
      Invite,
      {
        copy: screen.name === 'invite-copy',
        back
      }
    );
  }

  if (
    screen.name
    === 'manager-uninstall'
  ) {
    return h(
      Confirm,
      {
        title: 'Uninstall Bot Manager',
        message:
          'Remove the local jnbot command? Bot data and private settings stay in place.',
        back,
        confirm:
          async () => {
            await bridge('manager-uninstall');
            done('Bot Manager command removed. This open session will keep working.');
          }
      }
    );
  }

  if (
    screen.name
    === 'setup'
  ) {
    return h(
      Setup,
      {
        go,
        back
      }
    );
  }

  if (
    screen.name
    === 'photo-setup'
  ) {
    return h(
      PhotoSetup,
      {
        screen,
        go,
        back
      }
    );
  }

  if (
    screen.name
    === 'photo-clear'
  ) {
    return h(
      Confirm,
      {
        title: 'Disable photo destination',
        message: 'Stop routing new photo submissions?',
        back,
        confirm:
          async () => {
            await bridge('config-clear-photo');
            done('Photo destination disabled.');
          }
      }
    );
  }

  if (
    screen.name
    === 'setup-value'
  ) {
    const settings = {
      token: {
        title: 'Discord token',
        help: 'Paste the private bot token. It will not be shown.',
        name: 'DISCORD_TOKEN',
        secret: true
      },
      application: {
        title: 'Application ID',
        help: 'Enter the Discord application ID.',
        name: 'DISCORD_APPLICATION_ID',
        secret: false
      },
      'photo-server': {
        title: 'Photo destination server ID',
        help: 'A channel ID is also required.',
        name: 'MANAGEMENT_GUILD_ID',
        secret: false
      },
      'photo-channel': {
        title: 'Photo destination channel ID',
        help: 'The channel must be inside the configured server.',
        name: 'MANAGEMENT_CHANNEL_ID',
        secret: false
      },
      'photo-webhook': {
        title: 'Photo destination webhook',
        help: 'Paste a private Discord webhook URL. It will not be shown.',
        name: 'PHOTO_WEBHOOK_URL',
        secret: true
      }
    };

    const setting = settings[
      screen.setting
    ];

    return h(
      LineInput,
      {
        title: setting.title,
        help: setting.help,
        secret: setting.secret,
        back,
        submit:
          async value => {
            try {
              await bridge(
                'config-set',
                {
                  name: setting.name,
                  value
                }
              );

              done(
                screen.setting === 'token'
                || screen.setting === 'application'
                  ? `${setting.title} saved. Restart the bot to apply it.`
                  : screen.setting === 'photo-webhook'
                    ? `${setting.title} saved and active.`
                    : `${setting.title} saved. Complete both IDs to activate it.`
              );
            } catch (error) {
              done(error.message);
            }
          }
      }
    );
  }

  if (
    screen.name
    === 'servers'
  ) {
    return h(
      Servers,
      {
        go,
        back
      }
    );
  }

  if (
    screen.name
    === 'server'
  ) {
    return h(
      Server,
      {
        screen,
        go,
        back
      }
    );
  }

  if (
    screen.name
    === 'set-channel'
  ) {
    return h(
      LineInput,
      {
        title:
          `Set channel · ${screen.server.name}`,
        help:
          'Enter the Discord text channel ID.',
        initial:
          screen.server.channel_id
          || '',
        back,
        submit:
          async value => {
            try {
              await bridge(
                'queue',
                {
                  action:
                    'set_channel',
                  payload: {
                    guild_id:
                      screen.server.id,
                    channel_id:
                      value
                  }
                }
              );

              done(
                'Channel change queued.'
              );

            } catch (error) {
              done(
                error.message
              );
            }
          }
      }
    );
  }

  if (
    screen.name
    === 'server-ban'
  ) {
    const banning =
      screen.action
      === 'ban';

    return h(
      Confirm,
      {
        title:
          banning
            ? 'Ban server'
            : 'Unban server',
        message:
          banning
            ? (
                `Ban ${screen.server.name}? `
                + 'The bot will leave the server.'
              )
            : (
                `Remove the ban for `
                + `${screen.server.name}?`
              ),
        back,
        confirm:
          async () => {
            await bridge(
              'queue',
              {
                action:
                  banning
                    ? 'ban_server'
                    : 'unban_server',
                payload: {
                  guild_id:
                    screen.server.id
                }
              }
            );

            done(
              banning
                ? 'Server ban queued.'
                : 'Server unban queued.'
            );
          }
      }
    );
  }

  if (
    screen.name
    === 'server-delete'
  ) {
    return h(
      Confirm,
      {
        title:
          'Delete server data',
        message:
          (
            `Delete stored data for `
            + `${screen.server.name}?`
          ),
        back,
        confirm:
          async () => {
            await bridge(
              'queue',
              {
                action:
                  'delete_server_data',
                payload: {
                  guild_id:
                    screen.server.id
                }
              }
            );

            done(
              'Server data deletion queued.'
            );
          }
      }
    );
  }

  if (
    screen.name
    === 'posts'
  ) {
    return h(
      Posts,
      {
        go,
        back
      }
    );
  }

  if (
    screen.name
    === 'post'
  ) {
    return h(
      Post,
      {
        screen,
        go,
        back
      }
    );
  }

  if (
    screen.name
    === 'posts-addons'
  ) {
    return h(
      PostsAddons,
      {
        go,
        back
      }
    );
  }

  if (
    screen.name
    === 'photo-posts'
  ) {
    return h(PhotoPosts, {screen, go, back});
  }

  if (
    screen.name
    === 'post-action'
  ) {
    const post =
      screen.post;

    const map = {
      photos: {
        title:
          post.photo_requested
            ? 'Stop photo request'
            : 'Request photos',
        message:
          post.photo_requested
            ? 'Remove Submit Photos from this article?'
            : 'Add Submit Photos to this article?',
        action:
          'photo_request',
        payload: {
          post_id:
            post.post_id,
          enabled:
            !post.photo_requested
        }
      },
      withdraw: {
        title:
          'Withdraw post',
        message:
          'Delete this post from every server?',
        action:
          'withdraw_post',
        payload: {
          post_id:
            post.post_id
        }
      },
      restore: {
        title:
          'Restore post',
        message:
          'Allow this post to be delivered again?',
        action:
          'restore_post',
        payload: {
          post_id:
            post.post_id
        }
      },
      delete: {
        title:
          'Delete stored data',
        message:
          (
            'Delete local data for this post? '
            + 'Withdraw it first.'
          ),
        action:
          'delete_post_data',
        payload: {
          post_id:
            post.post_id
        }
      }
    };

    const action =
      map[screen.action];

    return h(
      Confirm,
      {
        title:
          action.title,
        message:
          action.message,
        back,
        confirm:
          async () => {
            try {
              await bridge(
                'queue',
                {
                  action:
                    action.action,
                  payload:
                    action.payload
                }
              );

              done(
                'Operator action queued.'
              );

            } catch (error) {
              done(
                error.message
              );
            }
          }
      }
    );
  }

  if (
    screen.name
    === 'activity'
  ) {
    return h(
      Activity,
      {
        back
      }
    );
  }

  if (
    screen.name
    === 'broadcast'
  ) {
    return h(Broadcasts, {go, back});
  }

  if (
    screen.name
    === 'broadcast-compose'
  ) {
    return h(
      LineInput,
      {
        title:
          'Broadcast',
        help:
          'Message every configured server.',
        back,
        submit:
          value => go({
            name:
              'broadcast-timing',
            value
          })
      }
    );
  }

  if (
    screen.name
    === 'broadcast-timing'
  ) {
    return h(
      Menu,
      {
        title: 'Broadcast Delivery',
        subtitle: 'Choose when to send this message.',
        back,
        items: [
          {id: 'now', label: 'Send Now'},
          {id: 'batch', label: 'Send With Next Post Batch'}
        ],
        select:
          item => go({
            name: 'broadcast-confirm',
            value: screen.value,
            delivery: item.id
          })
      }
    );
  }

  if (
    screen.name
    === 'broadcast-withdraw'
  ) {
    return h(
      Confirm,
      {
        title: 'Withdraw Broadcast',
        message:
          `Delete this broadcast from ${screen.broadcast.deliveries.length} server(s)?`,
        back,
        confirm:
          async () => {
            await bridge(
              'queue',
              {
                action: 'withdraw_broadcast',
                payload: {broadcast_id: screen.broadcast.id}
              }
            );
            done('Broadcast withdrawal queued.');
          }
      }
    );
  }

  if (
    screen.name
    === 'broadcast-confirm'
  ) {
    return h(
      Confirm,
      {
        title:
          screen.delivery === 'now'
            ? 'Send Broadcast Now'
            : 'Schedule Broadcast',
        message:
          screen.value,
        back,
        confirm:
          async () => {
            await bridge(
              'queue',
              {
                action:
                  screen.delivery === 'now'
                    ? 'broadcast'
                    : 'schedule_broadcast',
                payload: {
                  message:
                    screen.value
                }
              }
            );

            done(
              screen.delivery === 'now'
                ? 'Broadcast send requested.'
                : 'Broadcast scheduled for the next post batch.'
            );
          }
      }
    );
  }

  if (
    screen.name
    === 'updates'
  ) {
    return h(
      Updates,
      {
        go,
        back
      }
    );
  }

  if (
    screen.name
    === 'update-confirm'
  ) {
    return h(
      Confirm,
      {
        title: 'Install update',
        message:
          `Fast-forward main from ${screen.update.installed_revision} `
          + `to ${screen.update.available_revision}?`,
        back,
        confirm:
          async () => {
            try {
              const result = await bridge(
                'update-install'
              );

              done(
                `Updated to ${result.installed_revision}. `
                + 'Restart the bot to use the new code.'
              );
            } catch (error) {
              done(error.message);
            }
          }
      }
    );
  }

  if (
    screen.name
    === 'bot-action'
  ) {
    const action =
      screen.action;

    return h(
      Confirm,
      {
        title:
          'Bot control',
        message:
          `${action} the JunctionNow service?`,
        back,
        confirm:
          async () => {
            try {
              if (
                action === 'start'
              ) {
                await bridge(
                  'daemon-start'
                );
              } else if (
                action === 'stop'
              ) {
                await bridge(
                  'daemon-stop'
                );
              }

              done(
                `${action} requested.`
              );

            } catch (error) {
              done(
                error.message
              );
            }
          }
      }
    );
  }

  if (
    screen.name
    === 'message'
  ) {
    return h(
      Message,
      {
        title:
          screen.title,
        message:
          screen.message,
        back
      }
    );
  }

  return h(
    Message,
    {
      title:
        'Unknown screen',
      message:
        screen.name,
      back
    }
  );
}

render(
  h(App)
);
