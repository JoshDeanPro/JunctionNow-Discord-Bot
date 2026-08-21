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
      '◆ JunctionNow'
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
        ? '↑↓ move   enter select   ? help   esc exit'
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
        setIndex(
          value => Math.max(
            0,
            value - 1
          )
        );

        return;
      }

      if (
        key.downArrow
        || input === 'j'
      ) {
        setIndex(
          value => Math.min(
            items.length - 1,
            value + 1
          )
        );

        return;
      }

      if (
        key.return
        || key.rightArrow
      ) {
        if (items[index]) {
          select(
            items[index]
          );
        }

        return;
      }

      if (
        key.escape
        || key.leftArrow
      ) {
        if (back) {
          back();
        } else if (root) {
          exit();
        }
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
              key:
                `${item.id}-${itemIndex}`
            },
            h(
              Text,
              {
                color:
                  selected
                    ? BLUE
                    : DIM
              },
              selected
                ? '› '
                : '  '
            ),
            item.status
              ? h(
                  Text,
                  {
                    color:
                      item.statusColor
                      || MUTED
                  },
                  `${item.status} `
                )
              : null,
            h(
              Text,
              {
                bold: selected,
                color:
                  selected
                    ? BLUE
                    : undefined
              },
              item.label
            )
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
      Footer
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
      title: 'Operator Console',
      subtitle:
        'Local control for the JunctionNow Discord service.',
      items: [
        {
          id: 'dashboard',
          label: 'Dashboard'
        },
        {
          id: 'setup',
          label: 'Setup'
        },
        {
          id: 'servers',
          label: 'Servers'
        },
        {
          id: 'posts',
          label: 'Posts'
        },
        {
          id: 'photos',
          label: 'Photos'
        },
        {
          id: 'broadcast',
          label: 'Broadcast'
        },
        {
          id: 'activity',
          label: 'Activity'
        },
        {
          id: 'updates',
          label: 'Updates'
        },
        {
          id: 'bot',
          label: 'Bot'
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
        title: 'Dashboard error',
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
      'Dashboard'
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
        item => go({
          name: 'setup-value',
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
        'Latest tracked JunctionNow posts.',
      back,
      items:
        data.items.map(
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
        ),
      select:
        item => go({
          name: 'post',
          post: item.post
        })
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
          id: 'photos',
          label:
            post.photo_requested
              ? 'Stop requesting photos'
              : 'Request photos'
        },
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

function Photos({
  back
}) {
  const [data, setData] =
    useState(null);

  useEffect(
    () => {
      bridge('photos')
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
      title: 'Photos',
      subtitle:
        'Recent photo submissions.',
      back,
      items:
        data.items.length
          ? data.items.map(
              (item, index) => ({
                id:
                  `${index}-${item.at}`,
                label:
                  `${item.metadata?.file_count || 0} photo(s) · `
                  + `${item.metadata?.post_id || 'post'} · `
                  + `${item.metadata?.user_id || 'user'}`
              })
            )
          : [
              {
                id: 'none',
                label: 'No photo submissions'
              }
            ],
      select: () => {}
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
                  `${item.type} · ${item.at || ''}`
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

function Bot({
  go,
  back
}) {
  return h(
    Menu,
    {
      title: 'Bot',
      subtitle:
        'Daemon and feed controls.',
      back,
      items: [
        {
          id: 'start',
          label: 'Start daemon'
        },
        {
          id: 'stop',
          label: 'Stop daemon'
        },
        {
          id: 'pause',
          label: 'Pause feed delivery'
        },
        {
          id: 'resume',
          label: 'Resume feed delivery'
        }
      ],
      select:
        item => go({
          name: 'bot-action',
          action: item.id
        })
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
    === 'dashboard'
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
      'photo-destination': {
        title: 'Photo destination server',
        help: 'Enter the optional private Discord server ID.',
        name: 'MANAGEMENT_GUILD_ID',
        secret: false
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
                `${setting.title} saved. Restart the bot to apply it.`
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
    === 'photos'
  ) {
    return h(
      Photos,
      {
        back
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
              'broadcast-confirm',
            value
          })
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
          'Send broadcast',
        message:
          screen.value,
        back,
        confirm:
          async () => {
            await bridge(
              'queue',
              {
                action:
                  'broadcast',
                payload: {
                  message:
                    screen.value
                }
              }
            );

            done(
              'Broadcast queued.'
            );
          }
      }
    );
  }

  if (
    screen.name
    === 'bot'
  ) {
    return h(
      Bot,
      {
        go,
        back
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
              } else {
                await bridge(
                  'queue',
                  {
                    action: 'feed',
                    payload: {
                      enabled:
                        action
                        === 'resume'
                    }
                  }
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
